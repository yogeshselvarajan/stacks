from stacks.hitl.classify import Tier, Workflow
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
    """

    def __init__(self, tool_name: str, tool_input: dict, interrupt_response=None):
        self.tool_use = _FakeToolUse(name=tool_name, input=tool_input)
        self.cancel_tool = False
        self._interrupt_response = interrupt_response
        self.interrupt_calls: list[tuple[str, object]] = []

    def interrupt(self, name: str, reason=None):
        self.interrupt_calls.append((name, reason))
        return self._interrupt_response


def _hook_with_room_conflict_cached(sensitivity_flags):
    cache = EvaluationCache()
    cache.put("b1:b2", {
        "conflict_id": "b1:b2",
        "sensitivity_flags": [f.value for f in sensitivity_flags],
        "applicable_policy_clause": {"policy_name": "room_booking_priority", "clause_id": "RBP-1", "clause_text": "..."},
        "candidate_resolutions": [{"booking_id_that_yields": "b1", "booking_id_that_keeps": "b2", "deterministic_score": 1.0, "rule_applied": "RBP-1"}],
        "tie": False,
    })
    hook = HitlGateHook(cache, EvaluationCache(), EvaluationCache())
    return hook


def test_green_case_never_calls_interrupt():
    hook = _hook_with_room_conflict_cached([])
    event = _FakeEvent("resolve_room_conflict", {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_red_case_without_approval_raises_interrupt_and_cancels_on_no_response():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("resolve_room_conflict", {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert len(event.interrupt_calls) == 1
    assert event.interrupt_calls[0][1]["tier"] == "RED"
    assert event.cancel_tool != False  # noqa: E712 -- cancel_tool holds a message string, not just a bool


def test_red_case_with_valid_prior_approval_never_interrupts():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent(
        "resolve_room_conflict",
        {
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {"token": "t", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:b1:b2"},
        },
    )
    hook._gate(event)
    assert event.interrupt_calls == []
    assert event.cancel_tool is False


def test_evaluate_calls_are_never_gated():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("resolve_room_conflict", {"action": "evaluate", "conflicting_booking_ids": ["b1", "b2"]})
    hook._gate(event)
    assert event.interrupt_calls == []


def test_unrelated_tool_calls_are_ignored():
    hook = _hook_with_room_conflict_cached([SensitivityFlag.MINOR_ACCOUNT])
    event = _FakeEvent("get_library_data", {"query_type": "room_calendar"})
    hook._gate(event)
    assert event.interrupt_calls == []
