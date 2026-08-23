from datetime import datetime, timezone
from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.data.models import BookingRecord, BookingType
from stacks.hitl.classify import Tier, Workflow
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


# Core workflow tests (original)
def test_evaluate_ranks_recurring_program_above_one_off_renter():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    assert result["status"] == "success"
    body = result["content"][0]["json"]
    assert body["candidate_resolutions"][0]["booking_id_that_yields"] == "b_oneoff_a"
    assert body["sensitivity_flags"] == []


def test_evaluate_rejects_non_overlapping_bookings():
    tool_fn, repo, _ = _build()
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


# Missing test coverage: error conditions
def test_cross_tenant_denial():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_other", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    assert result["status"] == "error"
    assert "cross_tenant_denied" in result["content"][0]["text"]


def test_not_found_nonexistent_booking_id():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_nonexistent"])
    assert result["status"] == "error"
    assert "not_found" in result["content"][0]["text"]


def test_policy_not_found():
    repo = InMemoryLibraryDataRepository()
    repo.save_booking(BookingRecord(
        booking_id="b_1", library_id="lib_empty", room_id="room_a",
        start=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        booked_by="patron_1", booking_type=BookingType.RECURRING_PROGRAM,
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_2", library_id="lib_empty", room_id="room_a",
        start=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
        end=datetime(2026, 9, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_2", booking_type=BookingType.ONE_OFF_RENTER,
    ))
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_resolve_room_conflict(repo, cache, tier_ledger, "lib_empty")
    result = tool_fn(library_id="lib_empty", action="evaluate", conflicting_booking_ids=["b_1", "b_2"])
    assert result["status"] == "error"
    assert "policy_not_found" in result["content"][0]["text"]


def test_invalid_action():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", action="invalid_action", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    assert result["status"] == "error"
    assert "invalid_action" in result["content"][0]["text"]


def test_rationale_missing_clause_id_citation():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_oneoff_a", rationale="Some reason but missing clause_id",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_invalid_choice"


def test_red_commit_with_wrong_approver_role_rejected():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_b", "b_walkin_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        chosen_resolution_booking_id="b_walkin_b", rationale="Yields per RBP-1.",
        approval_token={"token": "tok_1", "approver_role": "branch_manager", "related_action_id": "room_conflict:b_recurring_b:b_walkin_b"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"


# Issue fixes: Fix 1 - duplicate booking ids
def test_duplicate_booking_ids_rejected():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_recurring_a"])
    assert result["status"] == "error"
    assert "duplicate" in result["content"][0]["text"]


# Issue fixes: Fix 1 - third unrelated booking rejection
def test_third_unrelated_booking_rejected():
    tool_fn, repo, _ = _build()
    repo.save_booking(BookingRecord(
        booking_id="b_other", library_id="lib_demo", room_id="room_b",
        start=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        booked_by="patron_3", booking_type=BookingType.WALK_IN,
    ))
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a", "b_other"])
    assert result["status"] == "error"
    assert "no_conflict_detected" in result["content"][0]["text"]


# Issue fixes: Fix 2 - token related_action_id mismatch
def test_token_with_mismatched_related_action_id_blocked():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_b", "b_walkin_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        chosen_resolution_booking_id="b_walkin_b", rationale="Yields per RBP-1.",
        approval_token={"token": "tok_1", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:wrong_conflict_id"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"


# Issue fixes: Fix 3 - idempotency (already_committed)
def test_second_commit_attempt_returns_already_committed():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    result1 = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_oneoff_a", rationale="Yields per RBP-1: recurring outranks one-off.",
    )
    assert result1["content"][0]["json"]["status"] == "committed"

    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"])
    result2 = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_a", "b_oneoff_a"],
        chosen_resolution_booking_id="b_oneoff_a", rationale="Yields per RBP-1: recurring outranks one-off.",
    )
    body = result2["content"][0]["json"]
    assert body["status"] == "already_committed"


# Issue fixes: Fix 4 - tie handling
def test_genuine_tie_returns_two_candidates_with_tie_flag():
    tool_fn, repo, _ = _build()
    repo.save_booking(BookingRecord(
        booking_id="b_tie_1", library_id="lib_demo", room_id="room_c",
        start=datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc),
        booked_by="patron_x", booking_type=BookingType.WALK_IN,
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_tie_2", library_id="lib_demo", room_id="room_c",
        start=datetime(2026, 9, 1, 14, 30, tzinfo=timezone.utc),
        end=datetime(2026, 9, 1, 15, 30, tzinfo=timezone.utc),
        booked_by="patron_y", booking_type=BookingType.WALK_IN,
    ))
    result = tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_tie_1", "b_tie_2"])
    body = result["content"][0]["json"]
    assert len(body["candidate_resolutions"]) == 2
    assert body["candidate_resolutions"][0]["deterministic_score"] == 0.0
    assert body["candidate_resolutions"][1]["deterministic_score"] == 0.0
    assert body["tie"] is True


def test_tie_blocks_commit_without_approval():
    tool_fn, repo, _ = _build()
    repo.save_booking(BookingRecord(
        booking_id="b_tie_a", library_id="lib_demo", room_id="room_d",
        start=datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc),
        booked_by="patron_a", booking_type=BookingType.STAFF_INTERNAL,
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_tie_b", library_id="lib_demo", room_id="room_d",
        start=datetime(2026, 9, 2, 14, 30, tzinfo=timezone.utc),
        end=datetime(2026, 9, 2, 15, 30, tzinfo=timezone.utc),
        booked_by="patron_b", booking_type=BookingType.STAFF_INTERNAL,
    ))
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_tie_a", "b_tie_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_tie_a", "b_tie_b"],
        chosen_resolution_booking_id="b_tie_b", rationale="Yields per RBP-1.",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"


def test_tie_commits_with_valid_approval():
    tool_fn, repo, _ = _build()
    repo.save_booking(BookingRecord(
        booking_id="b_tie_c", library_id="lib_demo", room_id="room_e",
        start=datetime(2026, 9, 3, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc),
        booked_by="patron_c", booking_type=BookingType.STAFF_INTERNAL,
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_tie_d", library_id="lib_demo", room_id="room_e",
        start=datetime(2026, 9, 3, 14, 30, tzinfo=timezone.utc),
        end=datetime(2026, 9, 3, 15, 30, tzinfo=timezone.utc),
        booked_by="patron_d", booking_type=BookingType.STAFF_INTERNAL,
    ))
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_tie_c", "b_tie_d"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_tie_c", "b_tie_d"],
        chosen_resolution_booking_id="b_tie_d", rationale="Yields per RBP-1.",
        approval_token={"token": "tok_tie", "approver_role": "librarian_case_review", "related_action_id": "room_conflict:b_tie_c:b_tie_d"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "committed"


# Issue fixes: Fix 5 - malformed approval_token
def test_malformed_approval_token_treated_as_none():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", action="evaluate", conflicting_booking_ids=["b_recurring_b", "b_walkin_b"])
    result = tool_fn(
        library_id="lib_demo", action="commit",
        conflicting_booking_ids=["b_recurring_b", "b_walkin_b"],
        chosen_resolution_booking_id="b_walkin_b", rationale="Yields per RBP-1.",
        approval_token={"token": "tok_1", "approver_role": "librarian_case_review"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"
