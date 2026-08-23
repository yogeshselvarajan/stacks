import pytest
from pydantic import ValidationError

from stacks.types import (
    ApprovalToken,
    PolicyClauseRef,
    SensitivityFlag,
    memory_namespace_for_patron,
)


def test_sensitivity_flag_values():
    assert SensitivityFlag.MINOR_ACCOUNT.value == "MINOR_ACCOUNT"
    assert SensitivityFlag.HARDSHIP_PATTERN.value == "HARDSHIP_PATTERN"
    assert SensitivityFlag.RARE_OR_SPECIAL_COLLECTIONS.value == "RARE_OR_SPECIAL_COLLECTIONS"
    assert SensitivityFlag.POLICY_EXCEPTION_REQUIRED.value == "POLICY_EXCEPTION_REQUIRED"


def test_policy_clause_ref_requires_all_fields():
    with pytest.raises(ValidationError):
        PolicyClauseRef(policy_name="room_booking_priority")


def test_approval_token_round_trip():
    token = ApprovalToken(token="tok_1", approver_role="librarian_case_review", related_action_id="room_conflict:b1:b2")
    assert token.model_dump() == {
        "token": "tok_1",
        "approver_role": "librarian_case_review",
        "related_action_id": "room_conflict:b1:b2",
    }


def test_memory_namespace_is_library_qualified():
    assert memory_namespace_for_patron("lib_demo", "patron_42") == "lib_demo:patron_42"
    # Different libraries must never collide on a bare patron id.
    assert memory_namespace_for_patron("lib_other", "patron_42") != memory_namespace_for_patron("lib_demo", "patron_42")
