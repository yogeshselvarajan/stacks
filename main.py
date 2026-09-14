# main.py
"""AgentCore Runtime entrypoint for Stacks, deployed via direct code
deployment (see this plan's Terraform/SDK-verification note). Wraps
build_stacks_agent behind BedrockAgentCoreApp's @app.entrypoint contract.

Two invocation modes, discriminated by payload["mode"]:
  - default (no "mode" key, or "chat"): a normal staff-facing prompt,
    matching what Plan 4's BFF will eventually send.
  - "overdue_sequencer_nightly_sweep": the EventBridge shim Lambda's
    (Task 8) nightly call, driving OverdueSequencer.run_nightly_tier for
    a fixed, configured list of circulation_record_ids.

No em dashes in this file's comments or strings.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.session.s3_session_manager import S3SessionManager

from stacks.agent import build_stacks_agent
from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink
from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
from stacks.identity.claims import StaffIdentityClaims
from stacks.memory.agentcore_store import AgentCoreMemoryStore
from stacks.sequencer.overdue_sequencer import OverdueSequencer

app = BedrockAgentCoreApp()

_REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
_ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
_MEMORY_ID = os.environ.get("STACKS_AGENTCORE_MEMORY_ID")
_SESSION_BUCKET = os.environ.get("STACKS_SESSION_BUCKET")

_repo = DynamoDBLibraryDataRepository(region=_REGION, environment=_ENVIRONMENT)
_memory = AgentCoreMemoryStore(memory_id=_MEMORY_ID, region=_REGION) if _MEMORY_ID else None


def _claims_from_payload(payload: dict) -> StaffIdentityClaims:
    return StaffIdentityClaims(
        role=payload["role"], library_id=payload["library_id"],
        case_review_role=payload.get("case_review_role"),
    )


@app.entrypoint
def invoke(payload: dict) -> dict:
    if payload.get("mode") == "overdue_sequencer_nightly_sweep":
        return _run_overdue_sweep(payload)
    return _run_chat(payload)


_SUCCESS_TOOL_OUTCOMES = {"committed", "no_match_recorded"}


def _all_audit_records(audit_sink, library_id: str) -> list:
    """DynamoDBAuditLogSink.all(library_id) requires library_id (a real,
    shared table); the in-memory AuditLogSink.all() takes no argument at
    all, already implicitly scoped to one process's own sink instance --
    mirrors bff/routes/reads.py's own _audit_all_for_library shim exactly,
    since this is the same "two sink shapes, one call site" problem."""
    import inspect

    if len(inspect.signature(audit_sink.all).parameters) == 0:
        return audit_sink.all()
    return audit_sink.all(library_id)


def _run_chat(payload: dict) -> dict:
    claims = _claims_from_payload(payload)
    session_id = payload["session_id"]
    pending_approvals_sink = DynamoDBPendingApprovalsSink(region=_REGION, environment=_ENVIRONMENT)
    audit_sink = DynamoDBAuditLogSink(region=_REGION, environment=_ENVIRONMENT)
    session_manager = (
        S3SessionManager(session_id=session_id, bucket=_SESSION_BUCKET, region_name=_REGION)
        if _SESSION_BUCKET else None
    )
    bundle = build_stacks_agent(
        _repo, claims, session_id=session_id,
        now=lambda: datetime.now(timezone.utc), memory=_memory,
        pending_approvals_sink=pending_approvals_sink, session_manager=session_manager,
        audit_sink=audit_sink,
    )
    result = bundle.agent(payload["prompt"])
    # I1 (Task 17 fix round): the BFF's write/resume endpoint needs to
    # know whether a resumed commit actually happened before it deletes
    # the PendingApprovals row and reports success -- stop_reason alone
    # cannot distinguish "committed" from "blocked_missing_approval"
    # (both finish the agent loop normally, not with stop_reason ==
    # "interrupt"). getattr guards test doubles (e.g.
    # tests/unit/test_main_entrypoint_wiring.py's _StubBundle) that don't
    # define audit_sink at all.
    #
    # Found live, 2026-09-14: a real Nova Lite invocation sometimes calls
    # the same tool an extra, redundant time after a genuine commit
    # already succeeded (e.g. re-checking route_ill_request after it was
    # already routed, which the tool correctly reports as an
    # "already_routed" error). Scoping to this invocation's own
    # session_id and preferring any real success outcome over a later,
    # merely-redundant error fixes a real false "needs_attention" report
    # on a request that had, in fact, already completed.
    result_bundle_audit_sink = getattr(bundle, "audit_sink", None)
    tool_outcome = None
    tool_name = payload.get("tool")
    if tool_name and result_bundle_audit_sink is not None:
        matching = [
            r for r in _all_audit_records(result_bundle_audit_sink, claims.library_id)
            if r.tool_name == tool_name and r.session_id == session_id
        ]
        if matching:
            success = next((r for r in matching if r.outcome in _SUCCESS_TOOL_OUTCOMES), None)
            tool_outcome = success.outcome if success is not None else matching[-1].outcome
    return {
        "message": str(result.message),
        "stop_reason": getattr(result, "stop_reason", None),
        "tool_outcome": tool_outcome,
    }


def _run_overdue_sweep(payload: dict) -> dict:
    if not _SESSION_BUCKET:
        return {"error": "STACKS_SESSION_BUCKET not configured"}

    claims = StaffIdentityClaims(role="circulation_staff", library_id=payload["library_id"], case_review_role=None)
    pending_approvals_sink = DynamoDBPendingApprovalsSink(region=_REGION, environment=_ENVIRONMENT)
    audit_sink = DynamoDBAuditLogSink(region=_REGION, environment=_ENVIRONMENT)

    def agent_factory(session_id: str):
        session_manager = S3SessionManager(session_id=session_id, bucket=_SESSION_BUCKET, region_name=_REGION)
        bundle = build_stacks_agent(
            _repo, claims, session_id=session_id, memory=_memory,
            pending_approvals_sink=pending_approvals_sink, session_manager=session_manager,
            audit_sink=audit_sink,
        )
        return bundle.agent

    sequencer = OverdueSequencer(bucket=_SESSION_BUCKET, region=_REGION, agent_factory=agent_factory)
    results = [
        sequencer.run_nightly_tier(circulation_record_id, payload["library_id"])
        for circulation_record_id in payload["circulation_record_ids"]
    ]
    return {"results": results}


if __name__ == "__main__":
    # host="0.0.0.0" is explicit, not left to BedrockAgentCoreApp.run()'s
    # own autodetection -- that autodetection only binds 0.0.0.0 when
    # /.dockerenv exists or DOCKER_CONTAINER is set, neither of which is
    # guaranteed true under AgentCore Runtime's direct-code-deployment
    # (non-container) execution path. See this plan's own
    # Terraform/SDK-verification note.
    app.run(host="0.0.0.0", port=8080)
