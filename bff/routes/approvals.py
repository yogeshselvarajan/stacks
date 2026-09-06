# bff/routes/approvals.py
"""The one write-capable route in the whole BFF. Every decision is
submitted as an InterruptResponseContent that resumes the paused agent
invocation the case is waiting on -- never a direct DynamoDB write. See
this plan's Verification note for the confirmed real interrupt/resume
contract this payload shape matches.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from stacks.hitl.classify import Tier, Workflow, is_approval_valid
from stacks.hitl.pending_approvals import PendingApprovalsSink
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import AgentRuntimeClient
from bff.deps import get_agent_runtime_client, get_current_claims, get_pending_approvals_sink

router = APIRouter()


class DecisionRequest(BaseModel):
    action: Literal["approve", "decline", "edit"]
    editedValue: str | None = None
    declineReason: str | None = None


@router.post("/api/approvals/{case_id}/decision")
async def submit_decision(
    case_id: str,
    body: DecisionRequest,
    claims: StaffIdentityClaims = Depends(get_current_claims),
    sink: PendingApprovalsSink = Depends(get_pending_approvals_sink),
    agent_runtime_client: AgentRuntimeClient = Depends(get_agent_runtime_client),
) -> dict:
    records = await run_in_threadpool(sink.list_for_library, claims.library_id)
    record = next((r for r in records if r.case_id == case_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="no pending case with that id for your library")

    tier = Tier(record.tier)
    workflow = Workflow(record.workflow)
    approver_role = claims.case_review_role if tier is Tier.RED else claims.role
    if not is_approval_valid(tier, approver_role, workflow):
        raise HTTPException(status_code=403, detail="your role cannot approve a case at this tier")

    response_payload = {
        "approved": body.action != "decline",
        "approver_role": approver_role,
        "token": f"hitl_resume:{case_id}",
        "edited_value": body.editedValue if body.action == "edit" else None,
    }
    invoke_payload = {
        "role": claims.role, "library_id": claims.library_id, "case_review_role": claims.case_review_role,
        "session_id": record.session_id,
        "prompt": [{"interruptResponse": {"interruptId": record.interrupt_id, "response": response_payload}}],
    }
    await run_in_threadpool(agent_runtime_client.invoke, invoke_payload)
    await run_in_threadpool(sink.delete, claims.library_id, case_id)
    return {"status": "ok"}
