# bff/routes/reads.py
"""Read-only BFF endpoints. Every one of these bypasses the agent
entirely -- a direct, IAM-scoped DynamoDB read through the repository/sink
Task 2 and Plan 3 already built, never a Bedrock call. Every query is
scoped to Depends(get_current_claims)'s own library_id, never a
client-supplied one -- this is the concrete mechanism closing the
cross-tenant trust gap frontend_architecture.md section 2 names.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.pending_approvals import PendingApprovalsSink
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims

from bff.deps import get_audit_sink, get_current_claims, get_pending_approvals_sink, get_repo
from bff.display_names import item_title, patron_name, room_name

router = APIRouter()

# LibraryDataRepository has no "list every room" method -- Plan 3's own
# scope note names the Spaces table as provisioned but deliberately unread
# by any tool. get_calendar with no room_id filter therefore queries this
# small, fixed list (the two rooms the demo dataset actually seeds,
# confirmed by reading src/stacks/data/fixtures.py directly: room_a and
# room_b) rather than a real room directory. A later plan that wires
# Spaces for real should replace this with a real
# repo.list_rooms(library_id) call; named here as a scope decision, not
# hidden as an unexplained hardcode.
_ROOM_BOOKING_ROOMS = ["room_a", "room_b"]

# Mirrors run_overdue_chase.py's own _ESCALATION_LADDER exactly (the tool
# is the single source of truth for tier ordering; this read endpoint
# never re-derives it independently). Display labels match the fixture
# convention in frontend/lib/fixtures/index.ts (e.g. "Fee mention").
_ESCALATION_LADDER = ["informational", "fee_mention", "hold_block", "collections_referral"]
_ESCALATION_LADDER_LABELS = {
    "informational": "Informational",
    "fee_mention": "Fee mention",
    "hold_block": "Hold block",
    "collections_referral": "Collections referral",
}


def _summary_for_pending(record, repo: LibraryDataRepository) -> tuple[str, list[dict] | None]:
    if record.workflow == "room_booking":
        booking_ids = record.case_id.split(":")
        bookings = [repo.get_booking(record.library_id, bid) for bid in booking_ids]
        candidates = [{"id": b.booking_id, "label": f"{b.booking_type.value} in {room_name(b.room_id)}"} for b in bookings if b is not None]
        return (f"Room-booking conflict: {' vs. '.join(c['label'] for c in candidates)}.", candidates or None)
    if record.workflow == "ill_routing":
        request = repo.get_ill_request(record.library_id, record.case_id)
        title = request.requested_title if request else record.case_id
        return (f"Ambiguous ILL routing for \"{title}\".", None)
    if record.workflow == "overdue_chase":
        return (f"Overdue escalation pending review for circulation record {record.case_id}.", None)
    return (record.case_id, None)


@router.get("/api/approvals")
async def get_approvals(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    sink: PendingApprovalsSink = Depends(get_pending_approvals_sink),
    repo: LibraryDataRepository = Depends(get_repo),
) -> list[dict]:
    records = await run_in_threadpool(sink.list_for_library, claims.library_id)
    now = datetime.now(timezone.utc)
    cases = []
    for r in records:
        summary, candidates = await run_in_threadpool(_summary_for_pending, r, repo)
        created_at = datetime.fromisoformat(r.created_at)
        age_minutes = int((now - created_at).total_seconds() // 60)
        cases.append({
            "caseId": r.case_id, "workflow": r.workflow, "tier": r.tier, "tool": r.tool,
            "summary": summary, "ageMinutes": max(age_minutes, 0), "candidates": candidates,
        })
    return cases


@router.get("/api/approvals/{case_id}")
async def get_approval_case(
    case_id: str,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    sink: PendingApprovalsSink = Depends(get_pending_approvals_sink),
    repo: LibraryDataRepository = Depends(get_repo),
) -> dict:
    records = await run_in_threadpool(sink.list_for_library, claims.library_id)
    matching = next((r for r in records if r.case_id == case_id), None)
    if matching is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="no pending case with that id for your library")
    summary, candidates = await run_in_threadpool(_summary_for_pending, matching, repo)
    return {
        "caseId": matching.case_id, "workflow": matching.workflow, "tier": matching.tier, "tool": matching.tool,
        "summary": summary, "ageMinutes": 0, "candidates": candidates,
    }


@router.get("/api/calendar")
async def get_calendar(
    room_id: str | None = None,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    repo: LibraryDataRepository = Depends(get_repo),
) -> list[dict]:
    rooms = [room_id] if room_id else _ROOM_BOOKING_ROOMS
    # The demo dataset's canonical room-booking conflict is seeded at a
    # fixed 2026-09-01/03 (fixtures.py) -- a narrow rolling window here
    # silently drops it out of view as real time passes (confirmed live:
    # a -7/+30 day window already hid it by 2026-09-12). Wide enough to
    # keep the demo dataset visible for the life of this project without
    # needing the fixture dates themselves to track wall-clock time.
    window_start = datetime.now(timezone.utc) - timedelta(days=60)
    window_end = datetime.now(timezone.utc) + timedelta(days=180)
    bookings = []
    for room in rooms:
        room_bookings = await run_in_threadpool(repo.get_bookings_for_room, claims.library_id, room, window_start, window_end)
        bookings.extend(room_bookings)
    return [
        {
            "bookingId": b.booking_id, "roomId": b.room_id, "roomName": room_name(b.room_id),
            "start": b.start.isoformat(), "end": b.end.isoformat(),
            "bookingType": b.booking_type.value, "status": b.status.value, "conflictResolution": None,
        }
        for b in bookings
    ]


@router.get("/api/ill-queue")
async def get_ill_queue(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    repo: LibraryDataRepository = Depends(get_repo),
    sink: PendingApprovalsSink = Depends(get_pending_approvals_sink),
) -> list[dict]:
    requests = await run_in_threadpool(repo.list_ill_requests, claims.library_id)
    pending = await run_in_threadpool(sink.list_for_library, claims.library_id)
    pending_tier_by_case = {r.case_id: r.tier for r in pending if r.workflow == "ill_routing"}
    return [
        {
            "illRequestId": r.ill_request_id,
            "requestedTitle": r.requested_title,
            "status": r.status.value,
            # None when there is no open pending-approval case for this
            # request (either already routed/no_match, or GREEN-classified
            # and committed without ever needing a human review) --
            # matches ApprovalCase's own tier source (the PendingApprovals
            # sink), never re-classified independently here.
            "tier": pending_tier_by_case.get(r.ill_request_id),
            # specialistTrace/recallSummary are optional on IllRequest and
            # need the ILL Disambiguation Specialist's own cache / a real
            # AgentCore Memory lookup respectively -- neither is wired
            # into this read endpoint (no memory/disambiguation_cache
            # dependency exists in the BFF), a named scope decision, not
            # a silent gap.
            "specialistTrace": None,
            "recallSummary": None,
        }
        for r in requests
    ]


def _tier_history_for_record(record, pending_case_ids: set[str]) -> list[dict]:
    """Builds the step-by-step tier history the frontend renders
    (overdue-queue-view.tsx). Mirrors run_overdue_chase.py's own
    prior_reminder_tier_sent semantics: every tier up to and including
    prior_reminder_tier_sent has been sent; the very next tier in the
    ladder is either awaiting human review (an open PendingApprovals case
    exists for this record) or simply not yet actioned. Tiers beyond that
    next one are not shown -- they have not been evaluated yet.
    """
    history = []
    for idx, ladder_name in enumerate(_ESCALATION_LADDER):
        if idx <= record.prior_reminder_tier_sent:
            status = "sent"
        elif idx == record.prior_reminder_tier_sent + 1:
            status = "held_for_review" if record.circulation_record_id in pending_case_ids else "pending"
        else:
            break
        history.append({"tierIndex": idx, "label": _ESCALATION_LADDER_LABELS[ladder_name], "status": status})
    return history


@router.get("/api/overdue-queue")
async def get_overdue_queue(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    repo: LibraryDataRepository = Depends(get_repo),
    sink: PendingApprovalsSink = Depends(get_pending_approvals_sink),
) -> list[dict]:
    records = await run_in_threadpool(repo.list_circulation_records, claims.library_id)
    pending = await run_in_threadpool(sink.list_for_library, claims.library_id)
    pending_case_ids = {r.case_id for r in pending if r.workflow == "overdue_chase"}
    now = datetime.now(timezone.utc)
    cases = []
    for record in records:
        # Mirrors run_overdue_chase.py's own not_overdue check
        # ((now - due_date).days <= 0) exactly, so this queue only ever
        # lists records the tool itself would actually act on.
        if record.returned or (now - record.due_date).days <= 0:
            continue
        cases.append({
            "circulationRecordId": record.circulation_record_id,
            "patronId": record.patron_id,
            "patronName": patron_name(record.patron_id),
            "itemTitle": item_title(record.item_id),
            "tierHistory": _tier_history_for_record(record, pending_case_ids),
            # recallSummary needs a real AgentCore Memory lookup, not
            # wired into this read endpoint -- named scope decision,
            # mirrors the same call made for ill-queue above.
            "recallSummary": None,
        })
    return cases


@router.get("/api/audit")
async def get_audit_list(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    sink: AuditLogSink = Depends(get_audit_sink),
) -> list[dict]:
    records = await run_in_threadpool(_audit_all_for_library, sink, claims.library_id)
    return [_serialize_audit_record(r) for r in records]


@router.get("/api/audit/{case_id}")
async def get_audit_trace(
    case_id: str,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    sink: AuditLogSink = Depends(get_audit_sink),
) -> list[dict]:
    records = await run_in_threadpool(_audit_all_for_library, sink, claims.library_id)
    return [_serialize_audit_record(r) for r in records if _record_belongs_to_case(r, case_id)]


def _record_belongs_to_case(record, case_id: str) -> bool:
    """Whether one audit record's tool_input actually concerns case_id.

    Mirrors _related_action_id_for_audit in src/stacks/hooks/audit_log.py
    exactly, per tool, since that is the one place this codebase already
    derives a case/action id from each mutating tool's own input shape --
    this does not invent a second convention. The one difference is
    notify_parties: its tool_input only carries the already-prefixed
    related_action_id ("room_conflict:...", "ill_request:...",
    "overdue:..."), computed by _derive_recipients in notify_parties.py
    as related_action_id.partition(":") -> (kind, case_id) -- so a
    notify_parties record matches when its related_action_id's suffix
    (after the first colon) equals case_id, for any of the three known
    prefixes.
    """
    tool_input = record.tool_input or {}
    if record.tool_name == "resolve_room_conflict":
        ids = tool_input.get("conflicting_booking_ids")
        return bool(ids) and ":".join(sorted(ids)) == case_id
    if record.tool_name == "route_ill_request":
        return tool_input.get("ill_request_id") == case_id
    if record.tool_name == "run_overdue_chase":
        return tool_input.get("circulation_record_id") == case_id
    if record.tool_name == "notify_parties":
        related_action_id = tool_input.get("related_action_id")
        return related_action_id in (
            f"room_conflict:{case_id}", f"ill_request:{case_id}", f"overdue:{case_id}",
        )
    return False


def _audit_all_for_library(sink: AuditLogSink, library_id: str) -> list:
    """DynamoDBAuditLogSink.all(library_id) requires library_id (Plan 3);
    the in-memory AuditLogSink.all() takes no argument at all (Plan 1) and
    is already implicitly scoped to one process's own sink instance --
    both are called correctly here via a small shim, since a bare
    sink.all(library_id) call would TypeError against the in-memory sink
    used by this task's own fast tests."""
    import inspect

    if len(inspect.signature(sink.all).parameters) == 0:
        return [r for r in sink.all() if r.library_id == library_id]
    return sink.all(library_id)


def _serialize_audit_record(r) -> dict:
    return {
        "auditId": r.audit_id, "sequence": r.sequence, "toolName": r.tool_name, "outcome": r.outcome,
        "actor": r.actor.value if hasattr(r.actor, "value") else r.actor,
        "actorIdentity": r.actor_identity, "timestamp": r.timestamp, "hitlTier": r.hitl_tier,
    }
