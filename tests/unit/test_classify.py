import pytest

from stacks.hitl.classify import (
    Tier,
    Workflow,
    classify_ill_routing,
    classify_overdue_chase,
    classify_room_conflict,
    is_approval_valid,
)
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.types import SensitivityFlag


def test_room_conflict_is_green_with_no_flags():
    assert classify_room_conflict([]) is Tier.GREEN


def test_room_conflict_is_red_with_any_flag():
    assert classify_room_conflict([SensitivityFlag.MINOR_ACCOUNT]) is Tier.RED


@pytest.mark.parametrize(
    "ambiguity,flags,expected",
    [
        ("none", [], Tier.GREEN),
        ("multiple_editions", [], Tier.YELLOW),
        ("no_match", [], Tier.YELLOW),
        ("policy_exception", [], Tier.RED),
        ("none", [SensitivityFlag.RARE_OR_SPECIAL_COLLECTIONS], Tier.RED),
        ("multiple_editions", [SensitivityFlag.POLICY_EXCEPTION_REQUIRED], Tier.RED),
        ("none", [SensitivityFlag.MINOR_ACCOUNT], Tier.RED),
        ("none", [SensitivityFlag.HARDSHIP_PATTERN], Tier.RED),
    ],
)
def test_ill_routing_classification_table(ambiguity, flags, expected):
    assert classify_ill_routing(ambiguity, flags) is expected


def test_ill_routing_rejects_unknown_ambiguity_value():
    with pytest.raises(ValueError):
        classify_ill_routing("not_a_real_value", [])


@pytest.mark.parametrize(
    "tier_consequence,flags,recalled_hardship,expected",
    [
        ("informational", [], False, Tier.GREEN),
        ("fee_mention", [], False, Tier.YELLOW),
        ("hold_block", [], False, Tier.YELLOW),
        ("collections_referral", [], False, Tier.RED),
        ("informational", [SensitivityFlag.HARDSHIP_PATTERN], False, Tier.RED),
        ("informational", [], True, Tier.RED),
        ("fee_mention", [], True, Tier.RED),
        ("hold_block", [], True, Tier.RED),
        ("collections_referral", [], True, Tier.RED),
    ],
)
def test_overdue_chase_classification_table(tier_consequence, flags, recalled_hardship, expected):
    assert classify_overdue_chase(tier_consequence, flags, recalled_hardship) is expected


def test_overdue_chase_rejects_unknown_tier_consequence_value():
    with pytest.raises(ValueError):
        classify_overdue_chase("not_a_real_value", [], False)


def test_green_requires_no_approval():
    assert is_approval_valid(Tier.GREEN, None, Workflow.ROOM_BOOKING) is True


def test_red_requires_exact_librarian_case_review_role():
    assert is_approval_valid(Tier.RED, "librarian_case_review", Workflow.ROOM_BOOKING) is True
    assert is_approval_valid(Tier.RED, "circulation_staff", Workflow.OVERDUE_CHASE) is False
    assert is_approval_valid(Tier.RED, None, Workflow.ROOM_BOOKING) is False


def test_yellow_requires_a_workflow_specific_allowed_role():
    assert is_approval_valid(Tier.YELLOW, "ill_coordinator", Workflow.ILL_ROUTING) is True
    assert is_approval_valid(Tier.YELLOW, "circulation_staff", Workflow.ILL_ROUTING) is False
    assert is_approval_valid(Tier.YELLOW, "circulation_staff", Workflow.OVERDUE_CHASE) is True
    assert is_approval_valid(Tier.YELLOW, "branch_manager", Workflow.ILL_ROUTING) is True
    assert is_approval_valid(Tier.YELLOW, "branch_manager", Workflow.OVERDUE_CHASE) is True
    assert is_approval_valid(Tier.YELLOW, "circulation_staff", Workflow.ROOM_BOOKING) is False


def test_evaluation_cache_put_and_get():
    cache = EvaluationCache()
    assert cache.get("case_1") is None
    cache.put("case_1", {"foo": "bar"})
    assert cache.get("case_1") == {"foo": "bar"}


def test_tier_ledger_record_and_get():
    ledger = TierLedger()
    assert ledger.get("room_conflict:b1:b2") is None
    ledger.record("room_conflict:b1:b2", Tier.RED, Workflow.ROOM_BOOKING)
    assert ledger.get("room_conflict:b1:b2") == (Tier.RED, Workflow.ROOM_BOOKING)
