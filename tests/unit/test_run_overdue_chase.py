from datetime import datetime, timezone

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.tools.run_overdue_chase import make_run_overdue_chase

_NOW = lambda: datetime(2026, 9, 1, tzinfo=timezone.utc)  # noqa: E731 -- fixed clock for deterministic tests


def _build():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_run_overdue_chase(repo, cache, tier_ledger, "lib_demo", _NOW)
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
