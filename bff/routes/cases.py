# bff/routes/cases.py
"""Case-creation endpoints -- the one place a new operational case enters
Stacks through the product itself, rather than a seed script or an ad hoc
engineering invocation of the real agent. Mirrors bff/routes/approvals.py's
own conventions exactly: authenticate via verified claims, never trust a
client-supplied tenant identity, call the same AgentRuntimeClient the
decision endpoint already uses.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from stacks.data.models import CirculationRecord, ILLRequestRecord
from stacks.data.repository import LibraryDataRepository
from stacks.hooks.audit_log import AuditLogRecord, AuditLogSink
from stacks.identity.claims import StaffIdentityClaims
from stacks.types import AuditActor, SensitivityFlag

from bff.clients.agent_runtime import AgentRuntimeClient
from bff.csrf import verify_csrf
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_repo
from bff.rate_limit import enforce_case_creation_rate_limit

router = APIRouter()

logger = logging.getLogger(__name__)


class CreateIllRequestBody(BaseModel):
    requestedTitle: str = Field(min_length=1)
    requestedEditionHint: str | None = None
    requesterPatronId: str = Field(min_length=1)


@router.post(
    "/api/ill-requests",
    dependencies=[Depends(verify_csrf), Depends(enforce_case_creation_rate_limit)],
)
async def create_ill_request(
    body: CreateIllRequestBody,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    repo: LibraryDataRepository = Depends(get_repo),
    audit_sink: AuditLogSink = Depends(get_audit_sink),
    agent_runtime_client: AgentRuntimeClient = Depends(get_agent_runtime_client),
) -> dict:
    ill_request_id = f"ill_{uuid.uuid4().hex[:12]}"
    record = ILLRequestRecord(
        ill_request_id=ill_request_id,
        library_id=claims.library_id,
        requested_title=body.requestedTitle,
        requested_edition_hint=body.requestedEditionHint,
        requester_patron_id=body.requesterPatronId,
    )
    await run_in_threadpool(repo.save_ill_request, record)

    await run_in_threadpool(
        audit_sink.append,
        AuditLogRecord(
            audit_id=str(uuid.uuid4()),
            sequence=None,
            tool_name="create_ill_request",
            tool_input={"ill_request_id": ill_request_id, "requested_title": body.requestedTitle},
            tool_output_status="success",
            outcome="created",
            session_id=f"case_create:{ill_request_id}",
            library_id=claims.library_id,
            actor=AuditActor.HUMAN,
            actor_identity=claims.role,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hitl_tier=None,
            notification_id=None,
        ),
    )

    invoke_payload = {
        "role": claims.role,
        "library_id": claims.library_id,
        "case_review_role": claims.case_review_role,
        "session_id": f"case_create_{ill_request_id}_{uuid.uuid4().hex[:8]}",
        "tool": "route_ill_request",
        "prompt": (
            f"Route the interlibrary loan request {ill_request_id} for library "
            f"{claims.library_id}. Evaluate it first, then, based on the "
            f"evaluation, commit the routing decision with a rationale citing "
            f"the applicable policy clause."
        ),
    }
    try:
        agent_response = await run_in_threadpool(agent_runtime_client.invoke, invoke_payload)
    except Exception:
        logger.exception("ill_request_agent_invocation_failed")
        # I1 (final review fix round): a case whose agent invocation itself
        # failed must not be left as a permanently orphaned record --
        # there is no future retry path that reuses this id (each new
        # "New request" submission always mints a fresh one), so leaving
        # it here would silently strand it forever, invisible to the ILL
        # Queue and unreachable by any workflow.
        await run_in_threadpool(repo.delete_ill_request, claims.library_id, ill_request_id)
        return {"illRequestId": ill_request_id, "status": "agent_invocation_failed", "outcome": None}

    if agent_response.get("stop_reason") == "interrupt":
        return {"illRequestId": ill_request_id, "status": "pending_approval", "outcome": None}

    # C1 (final review fix round): mirror approvals.py's own rule (lines
    # 98-105 there) exactly -- a non-interrupt stop_reason is not itself
    # proof the routing actually committed. Only report "resolved" when
    # the tool's own outcome says so; any other outcome (a blocked/
    # no-match/unrecognized result, or none at all) must surface as a
    # case that still needs a human to look at it, not a false success.
    outcome = agent_response.get("tool_outcome")
    if outcome == "committed":
        return {"illRequestId": ill_request_id, "status": "resolved", "outcome": outcome}
    return {"illRequestId": ill_request_id, "status": "needs_attention", "outcome": outcome}


class CreateOverdueCaseBody(BaseModel):
    patronId: str = Field(min_length=1)
    itemId: str = Field(min_length=1)
    itemType: str = Field(min_length=1)
    daysOverdue: int = Field(gt=0)
    sensitivityFlag: bool = False


@router.post(
    "/api/overdue-cases",
    dependencies=[Depends(verify_csrf), Depends(enforce_case_creation_rate_limit)],
)
async def create_overdue_case(
    body: CreateOverdueCaseBody,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    repo: LibraryDataRepository = Depends(get_repo),
    audit_sink: AuditLogSink = Depends(get_audit_sink),
    agent_runtime_client: AgentRuntimeClient = Depends(get_agent_runtime_client),
) -> dict:
    circulation_record_id = f"circ_{uuid.uuid4().hex[:12]}"
    due_date = datetime.now(timezone.utc) - timedelta(days=body.daysOverdue)
    flags = [SensitivityFlag.MINOR_ACCOUNT] if body.sensitivityFlag else []
    record = CirculationRecord(
        circulation_record_id=circulation_record_id,
        library_id=claims.library_id,
        patron_id=body.patronId,
        item_id=body.itemId,
        item_type=body.itemType,
        due_date=due_date,
        flags=flags,
    )
    await run_in_threadpool(repo.save_circulation_record, record)

    await run_in_threadpool(
        audit_sink.append,
        AuditLogRecord(
            audit_id=str(uuid.uuid4()),
            sequence=None,
            tool_name="create_overdue_case",
            tool_input={"circulation_record_id": circulation_record_id, "days_overdue": body.daysOverdue},
            tool_output_status="success",
            outcome="created",
            session_id=f"case_create:{circulation_record_id}",
            library_id=claims.library_id,
            actor=AuditActor.HUMAN,
            actor_identity=claims.role,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hitl_tier=None,
            notification_id=None,
        ),
    )

    invoke_payload = {
        "role": claims.role,
        "library_id": claims.library_id,
        "case_review_role": claims.case_review_role,
        "session_id": f"case_create_{circulation_record_id}_{uuid.uuid4().hex[:8]}",
        "tool": "run_overdue_chase",
        "prompt": (
            f"Run the overdue-item chase for circulation record {circulation_record_id} in library "
            f"{claims.library_id}. Evaluate it first, then, based on the evaluation, commit the "
            f"escalation with a message body citing the applicable policy clause."
        ),
    }
    try:
        agent_response = await run_in_threadpool(agent_runtime_client.invoke, invoke_payload)
    except Exception:
        logger.exception("overdue_case_agent_invocation_failed")
        await run_in_threadpool(repo.delete_circulation_record, claims.library_id, circulation_record_id)
        return {"circulationRecordId": circulation_record_id, "status": "agent_invocation_failed", "outcome": None}

    if agent_response.get("stop_reason") == "interrupt":
        return {"circulationRecordId": circulation_record_id, "status": "pending_approval", "outcome": None}
    tool_outcome = agent_response.get("tool_outcome")
    if tool_outcome == "committed":
        return {"circulationRecordId": circulation_record_id, "status": "resolved", "outcome": tool_outcome}
    return {"circulationRecordId": circulation_record_id, "status": "needs_attention", "outcome": tool_outcome}
