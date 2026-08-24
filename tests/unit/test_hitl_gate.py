import pytest

from strands.interrupt import InterruptException

from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.hitl_gate import HitlGateHook
from stacks.types import SensitivityFlag


class _FakeToolUse(dict):
    """Minimal duck-typed stand-in for Strands' ToolUse dict."""


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

    def interrupt(self, name: str, reason=None):
        self.interrupt_calls.append((name, reason))
        if self._interrupt_response is None:
            raise InterruptException(name)
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
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache())
    return hook


def _hook_with_ill_cached(ambiguity, sensitivity_flags):
    cache = EvaluationCache()
    cache.put("lib_demo", "ill_req_123", {
        "ill_request_id": "ill_req_123",
        "ambiguity": ambiguity,
        "sensitivity_flags": [f.value for f in sensitivity_flags],
        "applicable_policy_clause": {"policy_name": "ill_routing_policy", "clause_id": "IRP-1", "clause_text": "..."},
        "candidate_routes": [{"destination_library": "library_a", "estimated_wait": 5}],
    })
    hook = HitlGateHook(EvaluationCache(), cache, EvaluationCache())
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
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache())
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


def test_ill_gate_reads_resolved_via_substitution_from_tool_input_not_evaluation():
    """The convergence flag is only known at commit time (the specialist
    runs between evaluate and commit), so the gate must read it from the
    commit call's own tool_input, not from the cached evaluate() output
    (which was computed before the specialist ran and cannot contain it)."""
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
    hook._gate(event)
    # A convergent substitution with an actual chosen holding is GREEN --
    # the gate must not raise an interrupt.
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


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
