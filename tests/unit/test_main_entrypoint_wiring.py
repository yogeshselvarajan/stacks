"""Verifies main.py's own wiring, not build_stacks_agent's behavior
(already covered by tests/integration/test_stacks_agent.py). Monkeypatches
main.build_stacks_agent to a spy so no real Bedrock/DynamoDB/S3 call is
ever made -- constructing the real boto3-backed objects main.py passes in
is lazy and needs no credentials, but invoking the agent does, so this
test never calls the spy's return value's .agent.
"""
import os

import pytest


def _import_main(monkeypatch):
    monkeypatch.setenv("STACKS_AWS_REGION", "us-west-2")
    monkeypatch.setenv("STACKS_ENVIRONMENT", "dev")
    monkeypatch.setenv("STACKS_SESSION_BUCKET", "stacks-session-state-690845170953-us-west-2")
    monkeypatch.delenv("STACKS_AGENTCORE_MEMORY_ID", raising=False)
    import importlib
    import main as main_module
    importlib.reload(main_module)
    return main_module


def test_run_chat_constructs_a_real_s3_session_manager_and_pending_approvals_sink(monkeypatch):
    main_module = _import_main(monkeypatch)
    captured = {}

    def _spy_build_stacks_agent(repo, claims, session_id, now=None, memory=None, pending_approvals_sink=None, session_manager=None, audit_sink=None):
        captured["session_id"] = session_id
        captured["pending_approvals_sink"] = pending_approvals_sink
        captured["session_manager"] = session_manager
        captured["audit_sink"] = audit_sink
        class _StubBundle:
            def agent(self, prompt):
                return type("R", (), {"message": "stub", "stop_reason": "end_turn"})()
        return _StubBundle()

    monkeypatch.setattr(main_module, "build_stacks_agent", _spy_build_stacks_agent)

    payload = {"role": "branch_manager", "library_id": "lib_demo", "case_review_role": "librarian_case_review", "session_id": "sess_1", "prompt": "hello"}
    main_module._run_chat(payload)

    from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink
    from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
    from strands.session.s3_session_manager import S3SessionManager

    assert isinstance(captured["pending_approvals_sink"], DynamoDBPendingApprovalsSink)
    assert isinstance(captured["session_manager"], S3SessionManager)
    # Found live, 2026-09-14: build_stacks_agent always built its own
    # ephemeral, in-memory AuditLogSink with no way for a caller to reach
    # it, so every real tool commit's audit record was discarded the
    # moment the invocation ended. main.py must pass a real, persistent
    # sink instead.
    assert isinstance(captured["audit_sink"], DynamoDBAuditLogSink)
    assert captured["session_id"] == "sess_1"


def test_run_chat_prefers_a_real_success_outcome_over_a_later_redundant_error(monkeypatch):
    """Found live, 2026-09-14: Nova Lite sometimes calls the same tool an
    extra, redundant time after a genuine commit already succeeded (e.g.
    re-checking route_ill_request after it was already routed, which
    correctly errors "already_routed"). Taking the literal last matching
    audit record reported a false "needs_attention" for a request that
    had, in fact, already completed."""
    main_module = _import_main(monkeypatch)

    from stacks.hooks.audit_log import AuditLogRecord
    from stacks.types import AuditActor

    def _record(outcome: str) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id="a", tool_name="route_ill_request", tool_input={}, tool_output_status="success",
            outcome=outcome, session_id="sess_1", library_id="lib_demo", actor=AuditActor.AGENT,
            actor_identity=None, timestamp="2026-09-14T00:00:00+00:00", hitl_tier=None, notification_id=None,
        )

    class _StubAuditSink:
        def all(self):
            return [_record("success"), _record("committed"), _record("error")]

    def _spy_build_stacks_agent(repo, claims, session_id, now=None, memory=None, pending_approvals_sink=None, session_manager=None, audit_sink=None):
        class _StubBundle:
            audit_sink = _StubAuditSink()
            def agent(self, prompt):
                return type("R", (), {"message": "stub", "stop_reason": "end_turn"})()
        return _StubBundle()

    monkeypatch.setattr(main_module, "build_stacks_agent", _spy_build_stacks_agent)

    payload = {
        "role": "branch_manager", "library_id": "lib_demo", "case_review_role": "librarian_case_review",
        "session_id": "sess_1", "prompt": "route it", "tool": "route_ill_request",
    }
    result = main_module._run_chat(payload)

    assert result["tool_outcome"] == "committed"


def test_run_overdue_sweep_agent_factory_also_threads_a_session_manager(monkeypatch):
    """A fake OverdueSequencer that actually calls the real agent_factory
    it was constructed with (mirroring the real OverdueSequencer's own
    run_nightly_tier, which calls self._agent_factory(session_id)), so
    this test genuinely exercises main.py's agent_factory closure rather
    than short-circuiting past it."""
    main_module = _import_main(monkeypatch)
    captured_session_managers = []
    captured_audit_sinks = []

    def _spy_build_stacks_agent(repo, claims, session_id, now=None, memory=None, pending_approvals_sink=None, session_manager=None, audit_sink=None):
        captured_session_managers.append(session_manager)
        captured_audit_sinks.append(audit_sink)
        class _StubBundle:
            agent = None
        return _StubBundle()

    monkeypatch.setattr(main_module, "build_stacks_agent", _spy_build_stacks_agent)

    class _FakeOverdueSequencer:
        def __init__(self, bucket, region, agent_factory):
            self._agent_factory = agent_factory

        def run_nightly_tier(self, circulation_record_id, library_id):
            self._agent_factory(f"overdue:{library_id}:{circulation_record_id}")
            return {"circulation_record_id": circulation_record_id, "library_id": library_id, "tier_history_length": 0, "pending_approval": False}

    monkeypatch.setattr(main_module, "OverdueSequencer", _FakeOverdueSequencer)

    payload = {"library_id": "lib_demo", "circulation_record_ids": ["circ_1"]}
    main_module._run_overdue_sweep(payload)

    from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
    from strands.session.s3_session_manager import S3SessionManager
    assert len(captured_session_managers) == 1
    assert isinstance(captured_session_managers[0], S3SessionManager)
    assert isinstance(captured_audit_sinks[0], DynamoDBAuditLogSink)
