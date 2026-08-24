from datetime import datetime, timezone
from unittest.mock import MagicMock

from stacks.hooks.memory_event import MemoryEventHook
from stacks.memory.store import InMemoryMemoryStore


def _fake_after_tool_call_event(tool_name: str, tool_input: dict, result_json: dict):
    event = MagicMock()
    event.tool_use = {"name": tool_name, "input": tool_input}
    event.exception = None
    event.result = {"status": "success", "content": [{"json": result_json}]}
    return event


def test_fires_on_every_committed_ill_routing_decision_any_tier():
    store = InMemoryMemoryStore()
    hook = MemoryEventHook(store, library_id="lib_demo")

    event = _fake_after_tool_call_event(
        "route_ill_request",
        {"library_id": "lib_demo", "ill_request_id": "ill_1", "action": "commit"},
        {"ill_request_id": "ill_1", "status": "committed", "requester_patron_id": "patron_1", "resolved_via_substitution": True, "subject_area": "history"},
    )
    hook._record(event)

    pattern = store.get_ill_substitution_pattern("lib_demo", "patron_1")
    assert pattern is not None
    assert pattern.has_accepted_substitution_without_escalation is True


def test_does_not_fire_on_a_blocked_ill_routing_outcome():
    store = InMemoryMemoryStore()
    hook = MemoryEventHook(store, library_id="lib_demo")

    event = _fake_after_tool_call_event(
        "route_ill_request",
        {"library_id": "lib_demo", "ill_request_id": "ill_2", "action": "commit"},
        {"ill_request_id": "ill_2", "status": "blocked_missing_approval", "requester_patron_id": "patron_2"},
    )
    hook._record(event)

    assert store.get_ill_substitution_pattern("lib_demo", "patron_2") is None


def test_fires_on_a_red_overdue_commit_with_hardship_pattern_flag():
    store = InMemoryMemoryStore()
    hook = MemoryEventHook(store, library_id="lib_demo")

    event = _fake_after_tool_call_event(
        "run_overdue_chase",
        {"library_id": "lib_demo", "circulation_record_id": "circ_1", "action": "commit"},
        {
            "circulation_record_id": "circ_1", "status": "committed", "patron_id": "patron_3",
            "hitl_tier": "RED", "sensitivity_flags": ["HARDSHIP_PATTERN"],
        },
    )
    hook._record(event)

    fact = store.get_hardship_history("lib_demo", "patron_3")
    assert fact is not None


def test_does_not_fire_on_a_red_overdue_commit_for_collections_referral_alone():
    store = InMemoryMemoryStore()
    hook = MemoryEventHook(store, library_id="lib_demo")

    event = _fake_after_tool_call_event(
        "run_overdue_chase",
        {"library_id": "lib_demo", "circulation_record_id": "circ_2", "action": "commit"},
        {
            "circulation_record_id": "circ_2", "status": "committed", "patron_id": "patron_4",
            "hitl_tier": "RED", "sensitivity_flags": [],
        },
    )
    hook._record(event)

    assert store.get_hardship_history("lib_demo", "patron_4") is None


def test_does_not_fire_on_a_green_or_yellow_overdue_commit_even_with_hardship_flag_data():
    store = InMemoryMemoryStore()
    hook = MemoryEventHook(store, library_id="lib_demo")

    event = _fake_after_tool_call_event(
        "run_overdue_chase",
        {"library_id": "lib_demo", "circulation_record_id": "circ_3", "action": "commit"},
        {
            "circulation_record_id": "circ_3", "status": "committed", "patron_id": "patron_5",
            "hitl_tier": "YELLOW", "sensitivity_flags": ["HARDSHIP_PATTERN"],
        },
    )
    hook._record(event)

    assert store.get_hardship_history("lib_demo", "patron_5") is None
