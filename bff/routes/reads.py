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


def _summary_for_pending(record, repo: LibraryDataRepository) -> tuple[str, list[dict] | None]:
    if record.workflow == "room_booking":
        booking_ids = record.case_id.split(":")
        bookings = [repo.get_booking(record.library_id, bid) for bid in booking_ids]
        candidates = [{"id": b.booking_id, "label": f"{b.booking_type.value} in {b.room_id}"} for b in bookings if b is not None]
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
    window_start = datetime.now(timezone.utc) - timedelta(days=7)
    window_end = datetime.now(timezone.utc) + timedelta(days=30)
    bookings = []
    for room in rooms:
        room_bookings = await run_in_threadpool(repo.get_bookings_for_room, claims.library_id, room, window_start, window_end)
        bookings.extend(room_bookings)
    return [
        {
            "bookingId": b.booking_id, "roomId": b.room_id, "start": b.start.isoformat(), "end": b.end.isoformat(),
            "bookingType": b.booking_type.value, "status": b.status.value, "conflictResolution": None,
        }
        for b in bookings
    ]


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
    return [_serialize_audit_record(r) for r in records]


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
