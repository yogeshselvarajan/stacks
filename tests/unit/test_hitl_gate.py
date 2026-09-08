import pytest

from strands.interrupt import InterruptException

from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.hitl_gate import HitlGateHook
from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink
from stacks.types import SensitivityFlag


class _FakeToolUse(dict):
    """Minimal duck-typed stand-in for Strands' ToolUse dict."""


class _FakeInterrupt:
    """Minimal stand-in for strands.interrupt.Interrupt -- only the
    attributes HitlGateHook's PendingApprovals write actually reads."""

    def __init__(self, id: str, reason):
        self.id = id
        self.reason = reason


class _FakeInterruptState:
    """Minimal stand-in for strands.interrupt._InterruptState -- only the
    ``interrupts`` dict HitlGateHook._gate reads (to detect a resumed pass
    and recover tier from the persisted reason instead of the per-process
    EvaluationCache). Left empty by every _FakeEvent, since this fake
    models the SDK's two-pass mechanism as a single _gate() call (see
    _FakeEvent below) and never exercises the real cross-invocation
    session-restore path -- that gets its one true exercise in
    tests/integration/test_stacks_agent.py's
    test_resume_across_separate_agent_instances_completes_the_commit."""

    def __init__(self):
        self.interrupts: dict[str, object] = {}


class _FakeAgent:
    """Minimal stand-in for strands.Agent -- only the attribute
    HitlGateHook._gate reads off event.agent."""

    def __init__(self):
        self._interrupt_state = _FakeInterruptState()


class _FakeEvent:
    """Minimal duck-typed stand-in for BeforeToolCallEvent -- exercises
    HitlGateHook._gate directly without needing a live Strands Agent/model,
    per this plan's "Global Constraints" (zero AWS calls outside Task 11).
    The genuine strands.hooks.BeforeToolCallEvent + Agent.interrupt/resume
    mechanism gets its one true end-to-end exercise in Task 11.

    Models the real SDK's two-pass interrupt mechanism: raises InterruptException
    on first call (when no response yet), and returns the response on subsequent
    calls (after human input).
    """

    def __init__(self, tool_name: str, tool_input: dict, interrupt_response=None):
        self.tool_use = _FakeToolUse(name=tool_name, input=tool_input)
        self.cancel_tool = False
        self._interrupt_response = interrupt_response
        self.interrupt_calls: list[tuple[str, object]] = []
        self.agent = _FakeAgent()

    def interrupt(self, name: str, reason=None):
        self.interrupt_calls.append((name, reason))
        if self._interrupt_response is None:
            raise InterruptException(_FakeInterrupt(id=f"fake_interrupt:{name}", reason=reason))
        return self._interrupt_response


def _hook_with_room_conflict_cached(sensitivity_flags):
    cache = EvaluationCache()
    cache.put("lib_demo", "b1:b2", {
        "conflict_id": "b1:b2",
        "sensitivity_flags": [f.value for f in sensitivity_flags],
        "applicable_policy_clause": {"policy_name": "room_booking_priority", "clause_id": "RBP-1", "clause_text": "..."},
        "candidate_resolutions": [{"booking_id_that_yields": "b1", "booking_id_that_keeps": "b2", "deterministic_score": 1.0, "rule_applied": "RBP-1"}],
        "tie": False,
    })
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache(), EvaluationCache())
    return hook


def _hook_with_ill_cached(ambiguity, sensitivity_flags, disambiguation_cache=None):
    cache = EvaluationCache()
    cache.put("lib_demo", "ill_req_123", {
        "ill_request_id": "ill_req_123",
        "ambiguity": ambiguity,
        "sensitivity_flags": [f.value for f in sensitivity_flags],
        "applicable_policy_clause": {"policy_name": "ill_routing_policy", "clause_id": "IRP-1", "clause_text": "..."},
        "candidate_routes": [{"destination_library": "library_a", "estimated_wait": 5}],
    })
    hook = HitlGateHook(EvaluationCache(), cache, EvaluationCache(), disambiguation_cache or EvaluationCache())
    return hook


def test_green_case_never_calls_interrupt():
    hook = _hook_with_room_conflict_cached([])
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_red_case_without_approval_raises_interrupt_and_cancels_on_no_response():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"


def test_red_case_with_valid_prior_approval_never_interrupts():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {"token": "t", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:b1:b2"},
        },
    )
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_yellow_case_with_ill_routing():
    hook = _hook_with_ill_cached("multiple_editions", [])
    event = _FakeEvent("route_ill_request", {"library_id": "lib_demo", "action": "commit", "ill_request_id": "ill_req_123"})
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "YELLOW"


def test_red_case_approved_resume_sets_approval_token():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
        interrupt_response={"approved": True, "approver_role": "librarian_case_review"}
    )
    hook._gate(event)
    assert event.cancel_tool is False
    assert event.tool_use["input"]["approval_token"]["approver_role"] == "librarian_case_review"
    assert event.tool_use["input"]["approval_token"]["related_action_id"] == "room_conflict:b1:b2"


def test_red_case_denied_resume_cancels():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
        interrupt_response={"approved": False}
    )
    hook._gate(event)
    assert event.cancel_tool != False


def test_red_case_with_wrong_role_prior_token_falls_through_to_interrupt():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {"token": "t", "approver_role": "branch_manager", "related_action_id": "room_conflict:b1:b2"},
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"


def test_red_case_with_cross_case_token_falls_through_to_interrupt():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {"token": "t", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:different:case"},
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"


def test_cache_miss_cancels_without_interrupting():
    hook = _hook_with_room_conflict_cached([])
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["c1", "c2"]})
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool == "blocked_missing_evaluation"


def test_evaluate_calls_are_never_gated():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("resolve_room_conflict", {"action": "evaluate", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert event.interrupt_calls == []


def test_green_tied_room_conflict_still_raises_interrupt():
    """A genuine tie (two same-priority, unflagged, mutually-overlapping
    bookings) is GREEN tier by sensitivity_flags alone, but
    resolve_room_conflict's own commit path requires an approval token for
    any tie regardless of tier. Without this fix, the gate returned early
    at GREEN and never raised an interrupt, so no human was ever asked --
    an unresolvable dead end. Whole-branch review Important 5."""
    cache = EvaluationCache()
    cache.put("lib_demo", "b1:b2", {
        "conflict_id": "b1:b2",
        "sensitivity_flags": [],
        "applicable_policy_clause": {"policy_name": "room_booking_priority", "clause_id": "RBP-1", "clause_text": "..."},
        "candidate_resolutions": [
            {"booking_id_that_yields": "b1", "booking_id_that_keeps": "b2", "deterministic_score": 0.0, "rule_applied": "RBP-1"},
            {"booking_id_that_yields": "b2", "booking_id_that_keeps": "b1", "deterministic_score": 0.0, "rule_applied": "RBP-1"},
        ],
        "tie": True,
    })
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache(), EvaluationCache())
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "GREEN"


def test_green_non_tied_room_conflict_still_returns_early():
    """A non-tied GREEN case must still return early without interrupting --
    the tie-specific fix must not broaden to every GREEN case."""
    hook = _hook_with_room_conflict_cached([])
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_unrelated_tool_calls_are_ignored():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("get_library_data", {"query_type": "room_calendar"})
    hook._gate(event)
    assert event.interrupt_calls == []


def test_ill_gate_green_when_specialist_convergence_is_verified_in_cache():
    """The convergence flag is only known at commit time (the specialist
    runs between evaluate and commit), so the gate reads the raw claim
    from the commit call's own tool_input -- but only acts on it once
    verified against the disambiguation cache holding a matching,
    confident, non-ambiguous specialist result for this exact case and
    chosen holding (whole-branch review Critical 1)."""
    disambiguation_cache = EvaluationCache()
    disambiguation_cache.put("lib_demo", "ill_req_123", {
        "narrowed_candidate_id": "hold_2a", "confidence": 0.9, "still_ambiguous": False,
    })
    hook = _hook_with_ill_cached("multiple_editions", [], disambiguation_cache=disambiguation_cache)
    event = _FakeEvent(
        "route_ill_request",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "ill_request_id": "ill_req_123",
            "chosen_holding_id": "hold_2a",
            "resolved_via_substitution": True,
        },
    )
    hook._gate(event)
    # A verified convergent substitution with an actual chosen holding is
    # GREEN -- the gate must not raise an interrupt.
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_ill_gate_yellow_interrupt_when_resolved_via_substitution_claimed_without_specialist_cache():
    """CRITICAL regression test (whole-branch review Critical 1).
    Demonstrated exploitable during review: an ambiguous ILL request
    (ambiguity="multiple_editions") could be committed with
    resolved_via_substitution=True and a chosen holding id, auto-routing
    at GREEN with NO human approval and NO call to
    disambiguate_ill_candidates ever having happened -- the model simply
    asserted the flag. With no corresponding disambiguation_cache entry
    for this ill_request_id, the gate must now interrupt at YELLOW, not
    return early at GREEN."""
    hook = _hook_with_ill_cached("multiple_editions", [])
    event = _FakeEvent(
        "route_ill_request",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "ill_request_id": "ill_req_123",
            "chosen_holding_id": "hold_2a",
            "resolved_via_substitution": True,
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "YELLOW"


def test_ill_gate_no_holding_with_resolved_via_substitution_true_is_not_green():
    """resolved_via_substitution is definitionally a claim about having
    converged on a specific holding -- a commit with no chosen_holding_id
    (a no-match outcome) can never honestly be "resolved", regardless of
    the flag. Without this guard, the gate would classify this as GREEN
    and never interrupt, letting an ambiguous request close as NO_MATCH
    with no human ever asked (reviewer-confirmed bypass)."""
    hook = _hook_with_ill_cached("multiple_editions", [])
    event = _FakeEvent(
        "route_ill_request",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "ill_request_id": "ill_req_123",
            "chosen_holding_id": None,
            "resolved_via_substitution": True,
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "YELLOW"


def test_ill_gate_sensitivity_flag_overrides_convergent_substitution_at_red():
    """Gate-level mirror of classify.py's overriding rule: a sensitivity
    flag forces RED regardless of resolved_via_substitution=True."""
    hook = _hook_with_ill_cached("multiple_editions", [SensitivityFlag.RARE_OR_SPECIAL_COLLECTIONS])
    event = _FakeEvent(
        "route_ill_request",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "ill_request_id": "ill_req_123",
            "chosen_holding_id": "hold_2a",
            "resolved_via_substitution": True,
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"


def test_pending_approvals_sink_receives_a_write_when_an_interrupt_is_raised():
    sink = InMemoryPendingApprovalsSink()
    cache = EvaluationCache()
    cache.put("lib_demo", "b1:b2", {
        "conflict_id": "b1:b2",
        "sensitivity_flags": [SensitivityFlag.MINOR_ACCOUNT.value],
        "applicable_policy_clause": {"policy_name": "room_booking_priority", "clause_id": "RBP-1", "clause_text": "..."},
        "candidate_resolutions": [{"booking_id_that_yields": "b1", "booking_id_that_keeps": "b2", "deterministic_score": 1.0, "rule_applied": "RBP-1"}],
        "tie": False,
    })
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache(), EvaluationCache(), pending_approvals_sink=sink, session_id="sess_gate_test")
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})

    with pytest.raises(InterruptException):
        hook._gate(event)

    records = sink.list_for_library("lib_demo")
    assert len(records) == 1
    assert records[0].case_id == "b1:b2"
    assert records[0].tier == "RED"
    assert records[0].tool == "resolve_room_conflict"
    assert records[0].workflow == "room_booking"
    assert records[0].interrupt_id.startswith("fake_interrupt:")
    assert records[0].session_id == "sess_gate_test"


def test_no_pending_approvals_sink_is_backward_compatible():
    """A caller that doesn't pass pending_approvals_sink (every existing
    caller today) must keep working exactly as before -- no crash, no
    write attempted."""
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    with pytest.raises(InterruptException):
        hook._gate(event)  # must not raise anything else (e.g. AttributeError on a None sink)


def test_edit_value_overwrites_chosen_holding_id_on_ill_routing_resume():
    hook = _hook_with_ill_cached("multiple_editions", [])
    event = _FakeEvent(
        "route_ill_request",
        {"library_id": "lib_demo", "action": "commit", "ill_request_id": "ill_req_123", "chosen_holding_id": "hold_original"},
        interrupt_response={"approved": True, "approver_role": "ill_coordinator", "edited_value": "hold_edited"},
    )
    hook._gate(event)
    assert event.cancel_tool is False
    assert event.tool_use["input"]["chosen_holding_id"] == "hold_edited"


def test_edit_value_overwrites_chosen_resolution_booking_id_on_room_booking_resume():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"], "chosen_resolution_booking_id": "b1"},
        interrupt_response={"approved": True, "approver_role": "librarian_case_review", "edited_value": "b2"},
    )
    hook._gate(event)
    assert event.cancel_tool is False
    assert event.tool_use["input"]["chosen_resolution_booking_id"] == "b2"


def test_edit_value_is_ignored_for_overdue_chase_workflow():
    """OVERDUE_CHASE has no closed-world candidate field to edit
    (run_overdue_chase's commit takes free-text message_body, not a
    chosen candidate id) -- an edited_value in the response must not
    crash or silently invent a field."""
    cache = EvaluationCache()
    cache.put("lib_demo", "circ_1", {
        "circulation_record_id": "circ_1", "tier_consequence": "fee_mention",
        "sensitivity_flags": [], "has_recalled_hardship_history": False,
        "applicable_policy_clause": {"policy_name": "overdue_escalation", "clause_id": "OD-1", "clause_text": "..."},
    })
    hook = HitlGateHook(EvaluationCache(), EvaluationCache(), cache, EvaluationCache())
    event = _FakeEvent(
        "run_overdue_chase",
        {"library_id": "lib_demo", "action": "commit", "circulation_record_id": "circ_1"},
        interrupt_response={"approved": True, "approver_role": "circulation_staff", "edited_value": "should_be_ignored"},
    )
    hook._gate(event)
    assert event.cancel_tool is False
    # Proven vacuous by mutation testing: asserting "edited_value" is
    # absent from tool_input passes even if a future edit accidentally
    # mapped OVERDUE_CHASE to a real field, since no implementation ever
    # writes a literal "edited_value" key. Pin the actual field an
    # accidental mapping mistake would inject into instead.
    assert "message_body" not in event.tool_use["input"]
    assert set(event.tool_use["input"]) == {"library_id", "action", "circulation_record_id", "approval_token"}


def test_edit_value_is_not_applied_when_the_resumed_approval_is_invalid():
    """The edit passthrough must only apply after is_approval_valid
    succeeds, never before -- an invalid approver_role (or a denial) must
    both block the call (cancel_tool set) AND leave the field untouched,
    not silently smuggle the human's edited choice through on a rejected
    approval."""
    hook = _hook_with_ill_cached("multiple_editions", [])
    event = _FakeEvent(
        "route_ill_request",
        {"library_id": "lib_demo", "action": "commit", "ill_request_id": "ill_req_123", "chosen_holding_id": "hold_original"},
        # YELLOW tier requires ill_coordinator or branch_manager for
        # ILL_ROUTING (YELLOW_APPROVER_ROLES) -- "intern" is neither.
        interrupt_response={"approved": True, "approver_role": "intern", "edited_value": "hold_edited"},
    )
    hook._gate(event)
    assert event.cancel_tool == "blocked_missing_approval: tier=YELLOW"
    assert event.tool_use["input"]["chosen_holding_id"] == "hold_original"


def test_green_tied_room_conflict_edit_resume_succeeds_with_any_role():
    """Pins the current, intentional (inherited from Plan 1's tie-break
    fix) behavior: is_approval_valid(Tier.GREEN, ...) is unconditionally
    True for any role, so a tied GREEN room-conflict resume -- including
    an edited chosen_resolution_booking_id -- can be satisfied by any
    authenticated staff role, not only librarian_case_review. This test
    records that as a deliberate, tested decision so a future refactor
    cannot silently tighten or loosen it without a failing test."""
    cache = EvaluationCache()
    cache.put("lib_demo", "b1:b2", {
        "conflict_id": "b1:b2",
        "sensitivity_flags": [],
        "applicable_policy_clause": {"policy_name": "room_booking_priority", "clause_id": "RBP-1", "clause_text": "..."},
        "candidate_resolutions": [
            {"booking_id_that_yields": "b1", "booking_id_that_keeps": "b2", "deterministic_score": 0.0, "rule_applied": "RBP-1"},
            {"booking_id_that_yields": "b2", "booking_id_that_keeps": "b1", "deterministic_score": 0.0, "rule_applied": "RBP-1"},
        ],
        "tie": True,
    })
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache(), EvaluationCache())
    event = _FakeEvent(
        "resolve_room_conflict",
        {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"], "chosen_resolution_booking_id": "b1"},
        interrupt_response={"approved": True, "approver_role": "intern", "edited_value": "b2"},
    )
    hook._gate(event)
    assert event.cancel_tool is False
    assert event.tool_use["input"]["chosen_resolution_booking_id"] == "b2"
    assert event.tool_use["input"]["approval_token"]["approver_role"] == "intern"


def test_pending_approvals_sink_failure_does_not_swallow_the_interrupt():
    """A sink that raises on put() (e.g. a transient DynamoDB error) must
    never replace the InterruptException with the sink's own exception --
    the interrupt is the safety signal and must always propagate."""

    class _ExplodingSink:
        def put(self, record):
            raise RuntimeError("simulated transient sink failure")

        def delete(self, library_id, case_id):
            pass

        def list_for_library(self, library_id):
            return []

    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    hook._pending_approvals_sink = _ExplodingSink()
    event = _FakeEvent("resolve_room_conflict", {"library_id": "lib_demo", "action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    with pytest.raises(InterruptException):
        hook._gate(event)


def test_ill_gate_policy_exception_overrides_convergent_substitution_at_red():
    """Gate-level mirror of classify.py's overriding rule: ambiguity ==
    "policy_exception" forces RED regardless of resolved_via_substitution=True."""
    hook = _hook_with_ill_cached("policy_exception", [])
    event = _FakeEvent(
        "route_ill_request",
        {
            "library_id": "lib_demo",
            "action": "commit",
            "ill_request_id": "ill_req_123",
            "chosen_holding_id": "hold_2a",
            "resolved_via_substitution": True,
        },
    )
    with pytest.raises(InterruptException):
        hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"
