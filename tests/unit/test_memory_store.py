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
