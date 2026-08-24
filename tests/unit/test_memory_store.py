from datetime import datetime, timezone

from stacks.memory.store import InMemoryMemoryStore
from stacks.types import HardshipHistoryFact, RequesterSubstitutionPattern


def test_ill_substitution_pattern_round_trips_by_composite_namespace():
    store = InMemoryMemoryStore()
    assert store.get_ill_substitution_pattern("lib_demo", "patron_1") is None

    pattern = RequesterSubstitutionPattern(
        request_frequency=3, subject_areas=["history"],
        has_accepted_substitution_without_escalation=True,
        last_updated=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    store.set_ill_substitution_pattern("lib_demo", "patron_1", pattern)
    assert store.get_ill_substitution_pattern("lib_demo", "patron_1") == pattern


def test_ill_substitution_pattern_does_not_leak_across_library_id():
    store = InMemoryMemoryStore()
    pattern = RequesterSubstitutionPattern(
        request_frequency=1, subject_areas=[], has_accepted_substitution_without_escalation=False,
        last_updated=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    store.set_ill_substitution_pattern("lib_a", "patron_1", pattern)
    assert store.get_ill_substitution_pattern("lib_b", "patron_1") is None


def test_hardship_history_round_trips_and_is_library_scoped():
    store = InMemoryMemoryStore()
    assert store.get_hardship_history("lib_demo", "patron_2") is None

    fact = HardshipHistoryFact(flagged_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    store.set_hardship_history("lib_demo", "patron_2", fact)
    assert store.get_hardship_history("lib_demo", "patron_2") == fact
    assert store.get_hardship_history("lib_other", "patron_2") is None


def test_record_ill_routing_event_accumulates_frequency_and_subject_areas():
    store = InMemoryMemoryStore()

    # First call: frequency +2, subject_area "history", resolved_via_substitution=False
    store.record_ill_routing_event("lib_demo", "patron_x", 2, "history", False)
    pattern1 = store.get_ill_substitution_pattern("lib_demo", "patron_x")
    assert pattern1 is not None
    assert pattern1.request_frequency == 2
    assert pattern1.subject_areas == ["history"]
    assert pattern1.has_accepted_substitution_without_escalation is False

    # Second call: frequency +3, subject_area "science", resolved_via_substitution=True
    store.record_ill_routing_event("lib_demo", "patron_x", 3, "science", True)
    pattern2 = store.get_ill_substitution_pattern("lib_demo", "patron_x")
    assert pattern2 is not None
    assert pattern2.request_frequency == 5  # 2 + 3
    assert pattern2.subject_areas == ["history", "science"]
    assert pattern2.has_accepted_substitution_without_escalation is True

    # Third call: frequency +1, repeated subject_area "history", resolved_via_substitution=False
    store.record_ill_routing_event("lib_demo", "patron_x", 1, "history", False)
    pattern3 = store.get_ill_substitution_pattern("lib_demo", "patron_x")
    assert pattern3 is not None
    assert pattern3.request_frequency == 6  # 2 + 3 + 1
    assert pattern3.subject_areas == ["history", "science"]  # "history" not duplicated
    assert pattern3.has_accepted_substitution_without_escalation is True  # stays True, never flips back


def test_record_ill_routing_event_does_not_leak_across_library_id():
    store = InMemoryMemoryStore()

    # Record event for lib_a
    store.record_ill_routing_event("lib_a", "patron_1", 2, "history", False)

    # Verify lib_a has the event
    pattern_a = store.get_ill_substitution_pattern("lib_a", "patron_1")
    assert pattern_a is not None
    assert pattern_a.request_frequency == 2

    # Verify lib_b does not see the event
    pattern_b = store.get_ill_substitution_pattern("lib_b", "patron_1")
    assert pattern_b is None


def test_record_hardship_flag_directly():
    store = InMemoryMemoryStore()
    flagged_time = datetime(2026, 7, 15, 14, 30, 0, tzinfo=timezone.utc)

    # Call record_hardship_flag directly (not via set_hardship_history helper)
    store.record_hardship_flag("lib_demo", "patron_y", flagged_time)

    # Retrieve and verify
    fact = store.get_hardship_history("lib_demo", "patron_y")
    assert fact is not None
    assert fact.flagged_at == flagged_time


def test_record_hardship_flag_does_not_leak_across_library_id():
    store = InMemoryMemoryStore()
    flagged_time = datetime(2026, 7, 15, tzinfo=timezone.utc)

    # Record hardship flag for lib_a
    store.record_hardship_flag("lib_a", "patron_2", flagged_time)

    # Verify lib_a has it
    fact_a = store.get_hardship_history("lib_a", "patron_2")
    assert fact_a is not None
    assert fact_a.flagged_at == flagged_time

    # Verify lib_b does not see it
    fact_b = store.get_hardship_history("lib_b", "patron_2")
    assert fact_b is None
