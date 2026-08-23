from datetime import datetime, timedelta, timezone

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
