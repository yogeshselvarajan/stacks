from datetime import datetime, timezone

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.memory.store import InMemoryMemoryStore
from stacks.tools.run_overdue_chase import make_run_overdue_chase
from stacks.types import HardshipHistoryFact

_NOW = lambda: datetime(2026, 9, 1, tzinfo=timezone.utc)  # noqa: E731 -- fixed clock for deterministic tests


def _repo():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return repo


def _build():
    repo = _repo()
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_run_overdue_chase(repo, cache, tier_ledger, "lib_demo", _NOW, InMemoryMemoryStore())
    return tool_fn, repo, tier_ledger


def test_evaluate_first_tier_is_informational():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    body = result["content"][0]["json"]
    assert body["tier_consequence"] == "informational"
    assert body["days_overdue"] > 0
    assert body["has_recalled_hardship_history"] is False


def test_evaluate_already_at_top_tier_is_collections_referral():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_red", action="evaluate")
    body = result["content"][0]["json"]
    assert body["tier_consequence"] == "collections_referral"


def test_returned_item_is_not_overdue():
    tool_fn, repo, _ = _build()
    record = repo.get_circulation_record("lib_demo", "circ_green")
    record.returned = True
    repo.save_circulation_record(record)
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    assert result["content"][0]["json"]["status"] == "not_overdue"


def test_green_commit_succeeds_without_approval():
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Reminder per OD-1: your item is overdue.")
    body = result["content"][0]["json"]
    assert body["status"] == "committed"
    assert repo.get_circulation_record("lib_demo", "circ_green").prior_reminder_tier_sent == 0
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("lib_demo", "overdue:circ_green") == (Tier.GREEN, Workflow.OVERDUE_CHASE)


def test_red_commit_blocked_without_librarian_approval():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_red", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_red", action="commit", message_body="Escalation per OD-1.",
        approval_token={"token": "t", "approver_role": "circulation_staff", "related_action_id": "overdue:circ_red"},
    )
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_red_commit_succeeds_with_librarian_case_review():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_red", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_red", action="commit", message_body="Escalation per OD-1.",
        approval_token={"token": "t", "approver_role": "librarian_case_review", "related_action_id": "overdue:circ_red"},
    )
    assert result["content"][0]["json"]["status"] == "committed"


def test_commit_message_missing_policy_citation_is_blocked():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="A reminder with no citation.")
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_token_replay_across_records_is_rejected():
    """Token issued for one record cannot authorize action on a different record."""
    tool_fn, _, _ = _build()
    # Evaluate both records first to cache them
    tool_fn(library_id="lib_demo", circulation_record_id="circ_red", action="evaluate")
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    # Try to use a token minted for circ_red to commit circ_green (RED tier needs approval)
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Escalation per OD-1.",
        approval_token={"token": "t", "approver_role": "librarian_case_review", "related_action_id": "overdue:circ_red"},
    )
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_malformed_approval_token_treated_as_none():
    """Malformed token doesn't crash; treated as no token supplied."""
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    # Pass a malformed token (missing required fields)
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Reminder per OD-1: your item is overdue.",
        approval_token={"invalid": "structure"},
    )
    # Should succeed because GREEN tier doesn't require approval
    assert result["content"][0]["json"]["status"] == "committed"


def test_re_invoking_commit_for_the_same_tier_does_not_advance_or_recommit_it_twice():
    """Whole-branch review Important 4: AfterToolCallEvent fires after this
    tool has already mutated the repository and tier_ledger. If
    MemoryEventHook then rewrites event.result to an error (its
    fail-closed behavior), a caller that retries the same commit call
    would otherwise be treated as a fresh, legitimate commit -- re-running
    the same tier's notify/audit path a second time and, in the general
    case, risking a double-escalation. This mirrors resolve_room_conflict's
    own already_committed idempotency guard, keyed to the specific tier
    step (not the constant related_action_id, since run_overdue_chase is
    legitimately re-invoked every night for a NEW tier)."""
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    first = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Reminder per OD-1: your item is overdue.")
    assert first["content"][0]["json"]["status"] == "committed"
    assert repo.get_circulation_record("lib_demo", "circ_green").prior_reminder_tier_sent == 0

    # Re-invoke commit for the exact same case, no fresh evaluate -- as a
    # caller retrying after seeing an apparent (hook-injected) failure
    # would do.
    second = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Reminder per OD-1: your item is overdue.")
    body = second["content"][0]["json"]
    assert body["status"] == "already_committed"
    assert repo.get_circulation_record("lib_demo", "circ_green").prior_reminder_tier_sent == 0


def test_escalation_ladder_advances_over_multiple_cycles():
    """Record's tier must advance one step per cycle, not stay stuck at tier 0.
    Core test: the second evaluate should return a different tier than the first."""
    tool_fn, repo, _ = _build()

    # Cycle 1: evaluate tier 0 (informational) and commit
    result1 = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    tier0 = result1["content"][0]["json"]["tier_consequence"]
    assert tier0 == "informational", "First tier should be informational"
    commit1 = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="commit", message_body="Reminder per OD-1: your item is overdue.")
    assert commit1["content"][0]["json"]["status"] == "committed"

    # Cycle 2: evaluate should now return tier 1, not stay stuck at tier 0 (the original bug)
    result2 = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    tier1 = result2["content"][0]["json"]["tier_consequence"]
    assert tier1 == "fee_mention", f"Second evaluate should advance to fee_mention, not stay at {tier0}"

    # Verify the prior_reminder_tier_sent was updated after first commit
    record = repo.get_circulation_record("lib_demo", "circ_green")
    assert record.prior_reminder_tier_sent == 0, "After first commit, prior_reminder_tier_sent should be 0"


def test_cross_tenant_denial():
    """Tool denies cross-tenant requests at the boundary."""
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_other", circulation_record_id="circ_green", action="evaluate")
    assert result["status"] == "error"
    assert result["content"][0]["text"] == "cross_tenant_denied"


def test_message_body_with_collections_keyword_blocked_for_informational_tier():
    """Message body cannot contain severity keywords higher than the tier allows."""
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    # Try to commit informational tier with a collections-severity message
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit",
        message_body="Your account has been referred to collections per OD-1.",
    )
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_message_body_higher_tier_keyword_blocked():
    """Message body cannot reference a higher severity tier than recommended."""
    tool_fn, _ , _ = _build()

    # Evaluate circ_green (informational tier, tier 0)
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    # Try to commit with a hold-related keyword (tier 2) in an informational message
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit",
        message_body="Your account has been suspended per OD-1.",
    )
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_severity_check_uses_word_boundaries_not_substrings():
    """Ordinary words that merely contain a severity keyword as a substring
    -- "define" contains "fine", "household" and "threshold" both contain
    "hold" -- must not trip the guard. Only the standalone keyword itself
    should match."""
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit",
        message_body="Please define your household threshold per OD-1.",
    )
    assert result["content"][0]["json"]["status"] == "committed"


def test_evaluate_reads_recalled_hardship_history_within_recency_window():
    repo = _repo()  # reuse this file's existing fixture helper
    memory = InMemoryMemoryStore()
    memory.set_hardship_history("lib_demo", "patron_overdue_1", HardshipHistoryFact(
        flagged_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    ))
    tool_fn = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc), memory=memory,
    )
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    assert result["content"][0]["json"]["has_recalled_hardship_history"] is True


def test_evaluate_ignores_a_hardship_fact_outside_the_recency_window():
    repo = _repo()
    memory = InMemoryMemoryStore()
    memory.set_hardship_history("lib_demo", "patron_overdue_1", HardshipHistoryFact(
        flagged_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    ))
    tool_fn = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc), memory=memory,
    )
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    assert result["content"][0]["json"]["has_recalled_hardship_history"] is False


def test_evaluate_fails_closed_on_memory_retrieval_error():
    repo = _repo()

    class RaisingMemory:
        def get_hardship_history(self, library_id, patron_id):
            raise RuntimeError("simulated retrieval failure")

    tool_fn = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc), memory=RaisingMemory(),
    )
    result = tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    assert result["content"][0]["json"]["has_recalled_hardship_history"] is True


def test_committed_result_carries_patron_id_and_hitl_tier_for_memory_hook():
    repo = _repo()
    memory = InMemoryMemoryStore()
    tool_fn = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc), memory=memory,
    )
    tool_fn(library_id="lib_demo", circulation_record_id="circ_green", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", circulation_record_id="circ_green", action="commit",
        message_body="Per OD-1, this is your first reminder.",
    )
    body = result["content"][0]["json"]
    assert body["patron_id"] == "patron_overdue_1"
    assert body["hitl_tier"] == "GREEN"


def test_hardship_recency_window_works_end_to_end_through_the_real_hook_and_tool():
    """Regression test for the naive/aware datetime mismatch (whole-branch
    review Important 2). MemoryEventHook._record_hardship_flag used to
    write flagged_at=datetime.now() (timezone-naive), while this tool read
    it back and computed (now() - fact.flagged_at) where now() is
    timezone-aware -- raising TypeError, silently swallowed by this
    file's own fail-closed except Exception clause, which made
    has_recalled_hardship_history always True regardless of the fact's
    age. Neither Task 7's hook tests (fake store) nor Task 8's tool tests
    (facts seeded with already-aware datetimes directly) ever exercised
    the real write-then-read path, so this test writes a hardship fact
    through the REAL MemoryEventHook and reads it back through the REAL
    run_overdue_chase tool."""
    from datetime import timedelta
    from unittest.mock import MagicMock

    from stacks.data.models import CirculationRecord
    from stacks.hooks.memory_event import MemoryEventHook
    from stacks.types import SensitivityFlag

    repo = _repo()
    memory = InMemoryMemoryStore()
    hook = MemoryEventHook(memory, library_id="lib_demo")

    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_hardship_e2e", library_id="lib_demo",
        patron_id="patron_hardship_e2e", item_id="item_hardship_e2e", item_type="book",
        due_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        prior_reminder_tier_sent=3,
        flags=[SensitivityFlag.HARDSHIP_PATTERN],
    ))

    write_tool_fn = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc), memory=memory,
    )
    write_tool_fn(library_id="lib_demo", circulation_record_id="circ_hardship_e2e", action="evaluate")
    commit_result = write_tool_fn(
        library_id="lib_demo", circulation_record_id="circ_hardship_e2e", action="commit",
        message_body="Escalation per OD-1.",
        approval_token={"token": "t", "approver_role": "librarian_case_review", "related_action_id": "overdue:circ_hardship_e2e"},
    )
    assert commit_result["content"][0]["json"]["status"] == "committed"

    # Feed the tool's own real commit result through the REAL hook (real
    # datetime.now(timezone.utc) write, no fake store, no pre-seeded fact).
    event = MagicMock()
    event.tool_use = {
        "name": "run_overdue_chase",
        "input": {"library_id": "lib_demo", "circulation_record_id": "circ_hardship_e2e", "action": "commit"},
    }
    event.exception = None
    event.result = commit_result
    hook._record(event)

    # A `now` just 10 days after the real write is well within the
    # 365-day recency window -- must not raise, must recall the fact.
    read_within_window = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime.now(timezone.utc) + timedelta(days=10), memory=memory,
    )
    result_within = read_within_window(library_id="lib_demo", circulation_record_id="circ_hardship_e2e", action="evaluate")
    assert result_within["content"][0]["json"]["has_recalled_hardship_history"] is True

    # A `now` 400 days after the real write is outside the window --
    # before the fix, the naive/aware TypeError meant this always came
    # back True regardless of age; it must now correctly come back False.
    read_outside_window = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo",
        now=lambda: datetime.now(timezone.utc) + timedelta(days=400), memory=memory,
    )
    result_outside = read_outside_window(library_id="lib_demo", circulation_record_id="circ_hardship_e2e", action="evaluate")
    assert result_outside["content"][0]["json"]["has_recalled_hardship_history"] is False
