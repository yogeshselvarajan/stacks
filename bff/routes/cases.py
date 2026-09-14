# bff/routes/cases.py
"""Case-creation endpoints -- the one place a new operational case enters
Stacks through the product itself, rather than a seed script or an ad hoc
engineering invocation of the real agent. Mirrors bff/routes/approvals.py's
own conventions exactly: authenticate via verified claims, never trust a
client-supplied tenant identity, call the same AgentRuntimeClient the
decision endpoint already uses.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from stacks.data.models import ILLRequestRecord
from stacks.data.repository import LibraryDataRepository
from stacks.hooks.audit_log import AuditLogRecord, AuditLogSink
from stacks.identity.claims import StaffIdentityClaims
from stacks.types import AuditActor

from bff.clients.agent_runtime import AgentRuntimeClient
from bff.csrf import verify_csrf
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_repo

router = APIRouter()


class CreateIllRequestBody(BaseModel):
    requestedTitle: str = Field(min_length=1)
    requestedEditionHint: str | None = None
    requesterPatronId: str = Field(min_length=1)


@router.post("/api/ill-requests", dependencies=[Depends(verify_csrf)])
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
        return {"illRequestId": ill_request_id, "status": "agent_invocation_failed", "outcome": None}

    if agent_response.get("stop_reason") == "interrupt":
        return {"illRequestId": ill_request_id, "status": "pending_approval", "outcome": None}
    return {
        "illRequestId": ill_request_id,
        "status": "resolved",
        "outcome": agent_response.get("tool_outcome"),
    }
