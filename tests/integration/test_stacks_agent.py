import os
import tempfile
from datetime import datetime, timezone

import pytest
from strands.hooks import BeforeToolCallEvent
from strands.session.file_session_manager import FileSessionManager

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.agent import build_stacks_agent
from stacks.identity.claims import StaffIdentityClaims


def _build_bundle(monkeypatch):
    # build_stacks_agent fails closed if STACKS_BEDROCK_MODEL_ID is unset
    # (final_architecture.md section 4.2: the model ID is never hardcoded).
    # The two offline tests below only construct the Agent and inspect its
    # tool/hook registries -- they never invoke it -- so a syntactically
    # plausible placeholder is sufficient and is only injected when we are
    # NOT in a live-Bedrock run, so a real live run still fails loudly if
    # the operator forgot to set the real model ID themselves. Uses
    # monkeypatch (not a bare os.environ.setdefault) so the placeholder is
    # automatically un-set at the end of *this* test -- a bare setdefault
    # with no cleanup previously leaked STACKS_BEDROCK_MODEL_ID into every
    # later test in a full-suite run, wrongly "activating" other tests'
    # opt-in live-Bedrock smoke tests that gate on that same env var
    # (found while implementing Task 10 of Plan 2).
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    return build_stacks_agent(repo, claims, session_id="sess_test")


def test_build_stacks_agent_derives_library_id_from_claims(monkeypatch):
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")

    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    bundle = build_stacks_agent(repo, claims, session_id="sess_1", now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc))

    # get_library_data is scoped internally to session_library_id, derived
    # from claims.library_id. A query naming the same tenant string
    # ("lib_demo") must succeed -- if build_stacks_agent forgot to unwrap
    # claims.library_id and instead closed the tool over the whole claims
    # object, this same query would come back cross_tenant_denied because
    # "lib_demo" != <StaffIdentityClaims instance>.
    get_library_data_tool = bundle.agent.tool_registry.registry["get_library_data"]
    result = get_library_data_tool(
        library_id="lib_demo",
        query_type="room_calendar",
        room_calendar_filter={
            "room_id": "room_a",
            "start": "2026-09-01T00:00:00+00:00",
            "end": "2026-09-02T00:00:00+00:00",
        },
    )
    assert result["status"] == "success"


def test_build_stacks_agent_registers_all_six_tools(monkeypatch):
    bundle = _build_bundle(monkeypatch)
    tool_names = {t.tool_name for t in bundle.agent.tool_registry.registry.values()}
    assert tool_names == {
        "get_library_data",
        "resolve_room_conflict",
        "route_ill_request",
        "run_overdue_chase",
        "notify_parties",
        "disambiguate_ill_candidates",
    }


def test_build_stacks_agent_registers_all_three_hooks(monkeypatch):
    """Whole-branch review Important 3: the original version of this test
    (test_build_stacks_agent_registers_both_hooks) only checked
    HitlGateHook and AuditLogHook -- MemoryEventHook (added by Task 8) was
    asserted nowhere outside its own isolated unit test file. Same failure
    class as Plan 1's "provably vacuous safety-verification test": a test
    can pass even when a hook silently isn't wired into the real Agent."""
    from stacks.hitl.hitl_gate import HitlGateHook
    from stacks.hooks.audit_log import AuditLogHook
    from stacks.hooks.memory_event import MemoryEventHook
    from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent

    bundle = _build_bundle(monkeypatch)
    registry = bundle.agent.hooks
    before_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(BeforeToolCallEvent, [])}
    after_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(AfterToolCallEvent, [])}
    assert HitlGateHook in before_owners
    assert AuditLogHook in after_owners
    assert MemoryEventHook in after_owners


def test_build_stacks_agent_threads_memory_and_now_through_to_the_tools_that_need_them(monkeypatch):
    """Whole-branch review Important 3 (continued): registering the hook
    object is not enough on its own -- the memory and now constructor
    arguments must genuinely reach the tools that read them, not just
    exist as unused parameters. Constructs build_stacks_agent with a
    distinguishable sentinel MemoryStore and a fixed now(), drives real
    tool calls through the built Agent's own tool registry (bypassing the
    model, exactly like test_build_stacks_agent_derives_library_id_from_claims
    already does for get_library_data), and confirms both were actually
    reached -- not silently defaulted to InMemoryMemoryStore() or
    datetime.now()."""

    class _SpyMemoryStore:
        def __init__(self):
            self.get_ill_substitution_pattern_calls: list[tuple[str, str]] = []

        def get_ill_substitution_pattern(self, library_id, requester_key):
            self.get_ill_substitution_pattern_calls.append((library_id, requester_key))
            return None

        def record_ill_routing_event(self, *args, **kwargs):
            pass

        def get_hardship_history(self, library_id, patron_id):
            return None

        def record_hardship_flag(self, *args, **kwargs):
            pass

    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    spy_memory = _SpyMemoryStore()
    fixed_now = lambda: datetime(2026, 9, 5, tzinfo=timezone.utc)  # noqa: E731

    bundle = build_stacks_agent(repo, claims, session_id="sess_memory_now", now=fixed_now, memory=spy_memory)

    # memory: route_ill_request's evaluate action reads
    # get_ill_substitution_pattern -- the sentinel only sees this call if
    # build_stacks_agent actually threaded the passed-in memory object
    # through to make_route_ill_request, rather than defaulting to a
    # fresh InMemoryMemoryStore() internally.
    route_ill_request_tool = bundle.agent.tool_registry.registry["route_ill_request"]
    route_ill_request_tool(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    assert spy_memory.get_ill_substitution_pattern_calls == [("lib_demo", "patron_ill_2")]

    # now: run_overdue_chase's evaluate action computes days_overdue from
    # the injected now() -- a default datetime.now() would not produce
    # this exact, deterministic figure.
    run_overdue_chase_tool = bundle.agent.tool_registry.registry["run_overdue_chase"]
    result = run_overdue_chase_tool(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    body = result["content"][0]["json"]
    assert body["days_overdue"] == (fixed_now() - datetime(2026, 8, 20, tzinfo=timezone.utc)).days


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_green_room_booking_conflict_resolves_end_to_end_via_real_bedrock(monkeypatch):
    """The one test in this plan that makes a real Bedrock call. Exercises
    the full Agent + HitlGateHook + AuditLogHook wiring together, per this
    plan's Global Constraints note that only this test is allowed to touch
    AWS.
    """
    bundle = _build_bundle(monkeypatch)
    result = bundle.agent(
        "There is a room-booking conflict between booking b_recurring_a and "
        "booking b_oneoff_a in room_a. Resolve it per the room booking "
        "priority policy and notify both parties."
    )
    assert result.stop_reason != "interrupt"
    audit_records = bundle.audit_sink.all()
    assert any(r.tool_name == "resolve_room_conflict" and r.tool_output_status == "success" for r in audit_records)
    assert len(bundle.notification_sink.all()) >= 1


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_red_room_booking_conflict_interrupts_and_resumes_via_real_bedrock(monkeypatch):
    bundle = _build_bundle(monkeypatch)
    result = bundle.agent(
        "There is a room-booking conflict between booking b_recurring_b and "
        "booking b_walkin_b in room_b. Evaluate it and attempt to resolve "
        "it per the room booking priority policy."
    )
    assert result.stop_reason == "interrupt"
    assert len(result.interrupts) == 1

    responses = [{"interruptResponse": {"interruptId": result.interrupts[0].id, "response": None}}]
    bundle.agent(responses)
    # A None response (no approval_token supplied) must not silently commit --
    # cross-check against the audit trail's outcome field (the true
    # committed/blocked_missing_approval/already_committed/blocked_invalid_choice
    # outcome from the tool's own nested result, extracted by AuditLogHook's
    # _extract_outcome), not the envelope tool_output_status (which is
    # "success" for both a real commit and a blocked-but-well-formed
    # response) and not a substring check against tool_input (which only
    # ever contains the action name "commit", never the outcome string
    # "committed").
    audit_records = bundle.audit_sink.all()
    committed = [r for r in audit_records if r.tool_name == "resolve_room_conflict" and r.outcome == "committed"]
    assert committed == []


def test_build_stacks_agent_threads_session_manager_into_the_agent(monkeypatch):
    class _FakeSessionManager:
        def __init__(self):
            self.registered = False

        def register_hooks(self, registry, **kwargs):
            self.registered = True

    fake_session_manager = _FakeSessionManager()
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    bundle = build_stacks_agent(repo, claims, session_id="sess_sm", session_manager=fake_session_manager)

    assert bundle.agent._session_manager is fake_session_manager
    assert fake_session_manager.registered is True


def test_build_stacks_agent_with_no_session_manager_is_backward_compatible(monkeypatch):
    """Every existing caller omits session_manager -- must keep working
    exactly as before (agent._session_manager stays None, no hook added)."""
    bundle = _build_bundle(monkeypatch)
    assert bundle.agent._session_manager is None


def test_build_stacks_agent_threads_pending_approvals_sink_to_the_hitl_gate(monkeypatch):
    from stacks.hitl.hitl_gate import HitlGateHook
    from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink
    from strands.hooks import BeforeToolCallEvent

    sink = InMemoryPendingApprovalsSink()
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    bundle = build_stacks_agent(repo, claims, session_id="sess_pa", pending_approvals_sink=sink)

    hitl_gate_hooks = [
        cb.__self__ for cb in bundle.agent.hooks._registered_callbacks.get(BeforeToolCallEvent, [])
        if isinstance(cb.__self__, HitlGateHook)
    ]
    assert len(hitl_gate_hooks) == 1
    assert hitl_gate_hooks[0]._pending_approvals_sink is sink
    assert hitl_gate_hooks[0]._session_id == "sess_pa"


def test_build_stacks_agent_with_no_audit_sink_builds_its_own_ephemeral_one(monkeypatch):
    """Every existing caller and test omits audit_sink -- must keep
    working exactly as before (a fresh, in-memory AuditLogSink the caller
    can inspect via bundle.audit_sink)."""
    from stacks.hooks.audit_log import AuditLogSink

    bundle = _build_bundle(monkeypatch)
    assert isinstance(bundle.audit_sink, AuditLogSink)


def test_build_stacks_agent_threads_a_passed_audit_sink_into_the_hook_instead_of_building_one(monkeypatch):
    """main.py's real entrypoint must be able to pass a persistent
    DynamoDBAuditLogSink and have AuditLogHook actually write to it --
    found live, 2026-09-14: without this, every real tool commit's audit
    record was built correctly then discarded, since build_stacks_agent
    always built its own fresh, ephemeral sink no caller could reach."""
    from stacks.hooks.audit_log import AuditLogHook, AuditLogSink
    from strands.hooks import AfterToolCallEvent

    passed_sink = AuditLogSink()
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    bundle = build_stacks_agent(repo, claims, session_id="sess_audit", audit_sink=passed_sink)

    assert bundle.audit_sink is passed_sink
    audit_hooks = [
        cb.__self__ for cb in bundle.agent.hooks._registered_callbacks.get(AfterToolCallEvent, [])
        if isinstance(cb.__self__, AuditLogHook)
    ]
    assert len(audit_hooks) == 1
    assert audit_hooks[0]._sink is passed_sink


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_bff_shaped_edit_then_approve_resumes_correctly_via_real_bedrock(monkeypatch):
    """Exercises the exact InterruptResponseContent shape
    bff/routes/approvals.py builds (Task 17), including the edited_value
    passthrough (Task 3), against a real Agent + HitlGateHook +
    resolve_room_conflict, proving the BFF's write endpoint contract is
    correct before Task 18's real Runtime redeploy exists."""
    bundle = _build_bundle(monkeypatch)
    result = bundle.agent(
        "There is a room-booking conflict between booking b_recurring_b and "
        "booking b_walkin_b in room_b. Evaluate it and attempt to resolve "
        "it per the room booking priority policy."
    )
    assert result.stop_reason == "interrupt"
    interrupt_id = result.interrupts[0].id

    responses = [{"interruptResponse": {"interruptId": interrupt_id, "response": {
        "approved": True, "approver_role": "librarian_case_review", "token": "hitl_resume:b_recurring_b:b_walkin_b",
        "edited_value": "b_walkin_b",
    }}}]
    result = bundle.agent(responses)

    audit_records = bundle.audit_sink.all()
    committed = [r for r in audit_records if r.tool_name == "resolve_room_conflict" and r.outcome == "committed"]
    assert len(committed) == 1


def test_resume_across_separate_agent_instances_completes_the_commit(monkeypatch, tmp_path):
    """Every other resume test in this file (and in test_hitl_gate.py's
    _FakeEvent) resumes the SAME Agent/HitlGateHook/EvaluationCache
    instance that raised the interrupt in the first place. That is not
    how production actually works: a real AgentCore Runtime invocation
    is a brand-new process every time, and the BFF's write endpoint
    (bff/routes/approvals.py) resumes via a SEPARATE
    invoke_agent_runtime call from the one that raised the interrupt --
    meaning a fresh build_stacks_agent() call, and therefore a fresh,
    empty, in-process EvaluationCache that was never part of what gets
    persisted to the session.

    This test reproduces that exact cross-invocation shape for real,
    using a real Strands Agent, a real S3-shaped SessionManager
    (FileSessionManager, so it needs zero AWS credentials or cost), and
    the real HookRegistry/BeforeToolCallEvent/interrupt machinery -- the
    only thing stubbed out is the model call itself, since driving the
    hook directly (matching how the real event loop reuses the
    persisted tool_use_message on a resumed cycle, per
    strands/event_loop/event_loop.py) needs no model at all. Before the
    fix to HitlGateHook._gate (recovering tier from the interrupt's own
    persisted reason instead of re-deriving it from the empty cache),
    this reproduced a real bug: the second pass silently set
    event.cancel_tool = "blocked_missing_evaluation" instead of
    completing the resume, discarding the human's approval.
    """
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    session_id = "sess_cross_invocation_resume"
    storage_dir = str(tmp_path)

    def make_bundle():
        repo = InMemoryLibraryDataRepository()
        seed_demo_library(repo, library_id="lib_demo")
        claims = StaffIdentityClaims(
            role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
        )
        session_manager = FileSessionManager(session_id=session_id, storage_dir=storage_dir)
        return build_stacks_agent(repo, claims, session_id=session_id, session_manager=session_manager), session_manager

    # Invocation 1: raise the interrupt (matches the AgentCore Runtime call
    # the BFF's normal chat endpoint makes).
    bundle_1, session_manager_1 = make_bundle()
    agent_1 = bundle_1.agent
    resolve_tool = agent_1.tool_registry.registry["resolve_room_conflict"]

    eval_result = resolve_tool(
        library_id="lib_demo",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        action="evaluate",
    )
    assert eval_result["status"] == "success"

    tool_use = {
        "toolUseId": "tooluse_cross_invocation_1",
        "name": "resolve_room_conflict",
        "input": {
            "library_id": "lib_demo",
            "conflicting_booking_ids": ["b_recurring_b", "b_walkin_b"],
            "action": "commit",
            "chosen_resolution_booking_id": "b_walkin_b",
            "rationale": "per RBP-1",
        },
    }
    _, interrupts = agent_1.hooks.invoke_callbacks(
        BeforeToolCallEvent(agent=agent_1, selected_tool=resolve_tool, tool_use=tool_use, invocation_state={})
    )
    assert len(interrupts) == 1
    interrupt = interrupts[0]

    # Mirrors strands/event_loop/event_loop.py:527-530 (activate the
    # interrupt state after collecting interrupts) and the
    # AfterInvocationEvent -> sync_agent persistence step the real event
    # loop drives automatically.
    agent_1._interrupt_state.context = {
        "tool_use_message": {"role": "assistant", "content": [{"toolUse": tool_use}]},
        "tool_results": [],
    }
    agent_1._interrupt_state.activate()
    session_manager_1.sync_agent(agent_1)

    # Invocation 2: a SEPARATE process/Agent resumes the interrupt (matches
    # the BFF's write endpoint's own invoke_agent_runtime call).
    bundle_2, _session_manager_2 = make_bundle()
    agent_2 = bundle_2.agent
    assert agent_2._interrupt_state.activated is True

    prompt = [{"interruptResponse": {"interruptId": interrupt.id, "response": {
        "approved": True, "approver_role": "librarian_case_review",
        "token": "hitl_resume:cross_invocation", "edited_value": "b_walkin_b",
    }}}]
    agent_2._interrupt_state.resume(prompt)

    resumed_tool_use = agent_2._interrupt_state.context["tool_use_message"]["content"][0]["toolUse"]
    resolve_tool_2 = agent_2.tool_registry.registry["resolve_room_conflict"]
    resumed_event, resumed_interrupts = agent_2.hooks.invoke_callbacks(
        BeforeToolCallEvent(
            agent=agent_2, selected_tool=resolve_tool_2, tool_use=resumed_tool_use, invocation_state={}
        )
    )

    assert resumed_interrupts == []
    assert resumed_event.cancel_tool is False
    assert resumed_tool_use["input"]["approval_token"]["approver_role"] == "librarian_case_review"

    # The gate resuming successfully is necessary but not sufficient --
    # resolve_room_conflict's own commit path independently caches its
    # evaluation in the SAME process-local EvaluationCache, which is also
    # empty on this fresh Agent. Actually invoke the tool with the gate's
    # resumed tool_input (matching what the real event loop does next)
    # and confirm the commit itself completes, not just that the gate
    # stopped blocking it.
    commit_result = resolve_tool_2(**resumed_tool_use["input"])
    assert commit_result["content"][0]["json"]["status"] == "committed"
