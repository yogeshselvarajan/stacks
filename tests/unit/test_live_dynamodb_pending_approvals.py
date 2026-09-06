import os
import uuid

import pytest


def _sink():
    environment = os.environ.get("STACKS_TEST_DYNAMODB_ENVIRONMENT")
    if not environment:
        pytest.skip("STACKS_TEST_DYNAMODB_ENVIRONMENT not set -- run scripts/provision_pending_approvals_table.py first (Task 2)")
    from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink

    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    return DynamoDBPendingApprovalsSink(region=region, environment=environment)


def _record(library_id, case_id):
    from stacks.hitl.pending_approvals import PendingApprovalRecord

    return PendingApprovalRecord(
        library_id=library_id, case_id=case_id, tier="RED", tool="resolve_room_conflict",
        workflow="room_booking", reason={"tier": "RED"}, interrupt_id="v1:before_tool_call:abc",
        session_id="sess_1", created_at="2026-09-06T00:00:00+00:00",
    )


def test_live_put_then_list_for_library_returns_the_record():
    sink = _sink()
    library_id = f"lib_live_pending_{uuid.uuid4().hex}"
    sink.put(_record(library_id, "case_1"))
    records = sink.list_for_library(library_id)
    assert len(records) == 1
    assert records[0].case_id == "case_1"


def test_live_list_for_library_does_not_leak_across_library_id():
    sink = _sink()
    library_id_a = f"lib_live_pending_a_{uuid.uuid4().hex}"
    library_id_b = f"lib_live_pending_b_{uuid.uuid4().hex}"
    sink.put(_record(library_id_a, "case_1"))
    assert sink.list_for_library(library_id_b) == []


def test_live_delete_removes_the_record():
    sink = _sink()
    library_id = f"lib_live_pending_{uuid.uuid4().hex}"
    sink.put(_record(library_id, "case_1"))
    sink.delete(library_id, "case_1")
    assert sink.list_for_library(library_id) == []
