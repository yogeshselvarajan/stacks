from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.tools.resolve_room_conflict import make_resolve_room_conflict


def _build():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_resolve_room_conflict(repo, cache, tier_ledger, "lib_demo")
    return tool_fn, repo, tier_ledger


def test_evaluate_ranks_recurring_program_above_one_off_renter():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    assert result["status"] == "success"
    body = result["content"][0]["json"]
    assert body["candidate_resolutions"][0]["booking_id_that_yields"] == "b_oneoff_a"
    assert body["sensitivity_flags"] == []


def test_evaluate_rejects_non_overlapping_bookings():
    tool_fn, repo, _ = _build()
    from stacks.data.models import BookingRecord, BookingType
    from datetime import datetime, timezone
    repo.save_booking(BookingRecord(
        booking_id="b_far_away", library_id="lib_demo", room_id="room_a",
        start=datetime(2027, 1, 1, tzinfo=timezone.utc), end=datetime(2027, 1, 1, 1, tzinfo=timezone.utc),
        booked_by="patron_x", booking_type=BookingType.WALK_IN,
    ))
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_far_away"])
    assert result["status"] == "error"
    assert "no_conflict_detected" in result["content"][0]["text"]


def test_commit_without_prior_evaluate_is_rejected():
    tool_fn, _, _ = _build()
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_oneoff_a", rationale="per RBP-1",
    )
    assert result["status"] == "error"
    assert "evaluate_not_called" in result["content"][0]["text"]


def test_green_commit_succeeds_without_approval_token():
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_oneoff_a", rationale="Yields per RBP-1: recurring outranks one-off.",
    )
    assert result["status"] == "success"
    body = result["content"][0]["json"]
    assert body["status"] == "committed"
    assert body["calendar_write"]["yielding_booking_id"] == "b_oneoff_a"
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("room_conflict:b_oneoff_a:b_recurring_a") == (Tier.GREEN, Workflow.ROOM_BOOKING)


def test_red_commit_blocked_without_approval_token():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_b", "b_walkin_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        chosen_resolution_booking_id="b_walkin_b", rationale="Yields per RBP-1.",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"


def test_red_commit_succeeds_with_librarian_case_review_token():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_b", "b_walkin_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        chosen_resolution_booking_id="b_walkin_b", rationale="Yields per RBP-1.",
        approval_token={"token": "tok_1", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:b_recurring_b:b_walkin_b"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "committed"


def test_commit_with_choice_outside_candidate_set_is_rejected():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_recurring_a", rationale="Wrong choice, per RBP-1.",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_invalid_choice"
