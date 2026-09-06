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
from stacks.hitl.hitl_gate import _EDITABLE_FIELD_FOR_WORKFLOW
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

    # I2 (Task 17 fix round): action="edit" must never silently degrade
    # into a plain approve of the model's original proposal. Reject
    # up front, before ever touching the runtime, when there is no
    # edited value to apply or when this case's workflow has no
    # editable field at all (overdue_chase never does -- see
    # _EDITABLE_FIELD_FOR_WORKFLOW in hitl_gate.py).
    if body.action == "edit":
        if body.editedValue is None:
            raise HTTPException(status_code=400, detail="editedValue is required for action=edit")
        if workflow not in _EDITABLE_FIELD_FOR_WORKFLOW:
            raise HTTPException(status_code=400, detail="this case's workflow has no editable field")

    response_payload = {
        "approved": body.action != "decline",
        "approver_role": approver_role,
        "token": f"hitl_resume:{case_id}",
        "edited_value": body.editedValue if body.action == "edit" else None,
    }
    invoke_payload = {
        "role": claims.role, "library_id": claims.library_id, "case_review_role": claims.case_review_role,
        "session_id": record.session_id, "tool": record.tool,
        "prompt": [{"interruptResponse": {"interruptId": record.interrupt_id, "response": response_payload}}],
    }
    resume_response = await run_in_threadpool(agent_runtime_client.invoke, invoke_payload)

    # I1 (Task 17 fix round): a resumed invocation that hit a role
    # mismatch or invalid edit inside HitlGateHook/the tool itself
    # (cancel_tool set, nothing committed) must not be reported to the
    # caller as success, and its PendingApprovals row must not be
    # deleted -- the case must stay visible and actionable in the
    # Approval Inbox. main.py's _run_chat (the real Runtime entrypoint)
    # returns stop_reason and, when a "tool" key is present in the
    # payload, tool_outcome (the outcome of the last audit record for
    # that tool from this single invocation's own fresh in-process
    # AuditLogHook -- never cross-request/cross-tenant, since
    # build_stacks_agent constructs a brand-new AuditLogSink() per
    # invocation). stop_reason == "interrupt" means the resume did not
    # actually finish (still paused). For approve/edit, a genuinely
    # resolved outcome means the tool actually committed. For decline,
    # the tool committing anyway would itself be a severe anomaly
    # (a declined case must never commit).
    if resume_response.get("stop_reason") == "interrupt":
        raise HTTPException(status_code=502, detail="the resume did not complete; the case is still paused")

    tool_outcome = resume_response.get("tool_outcome")
    if body.action in ("approve", "edit") and tool_outcome != "committed":
        raise HTTPException(status_code=502, detail="the resume did not result in a committed action")
    if body.action == "decline" and tool_outcome == "committed":
        raise HTTPException(status_code=500, detail="the declined case was unexpectedly committed")

    await run_in_threadpool(sink.delete, claims.library_id, case_id)
    return {"status": "ok"}
