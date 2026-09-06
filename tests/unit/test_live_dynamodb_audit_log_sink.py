import os
import uuid

import pytest

from stacks.types import AuditActor


def _sink():
    environment = os.environ.get("STACKS_TEST_DYNAMODB_ENVIRONMENT")
    if not environment:
        pytest.skip("STACKS_TEST_DYNAMODB_ENVIRONMENT not set -- run infra/'s terraform apply first (Task 1)")
    from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink

    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    return DynamoDBAuditLogSink(region=region, environment=environment)


def _record(library_id: str, tool_name: str):
    from stacks.hooks.audit_log import AuditLogRecord

    return AuditLogRecord(
        audit_id=str(uuid.uuid4()), sequence=None, tool_name=tool_name, tool_input={"a": 1},
        tool_output_status="success", outcome="committed", session_id="sess_live", library_id=library_id,
        actor=AuditActor.AGENT, actor_identity=None, timestamp="2030-01-01T00:00:00+00:00",
        hitl_tier=None, notification_id=None,
    )


def test_live_append_assigns_a_monotonically_increasing_sequence():
    sink = _sink()
    library_id = f"lib_live_audit_{uuid.uuid4().hex}"
    first = _record(library_id, "resolve_room_conflict")
    second = _record(library_id, "notify_parties")
    sink.append(first)
    sink.append(second)
    assert first.sequence == 1
    assert second.sequence == 2


def test_live_all_returns_records_for_one_library_in_sequence_order():
    sink = _sink()
    library_id = f"lib_live_audit_{uuid.uuid4().hex}"
    sink.append(_record(library_id, "resolve_room_conflict"))
    sink.append(_record(library_id, "notify_parties"))
    records = sink.all(library_id)
    assert [r.tool_name for r in records] == ["resolve_room_conflict", "notify_parties"]
    assert all(isinstance(r.actor, AuditActor) for r in records)
    assert all(r.actor is AuditActor.AGENT for r in records)


def test_live_all_does_not_leak_across_library_id():
    sink = _sink()
    library_id_a = f"lib_live_audit_a_{uuid.uuid4().hex}"
    library_id_b = f"lib_live_audit_b_{uuid.uuid4().hex}"
    sink.append(_record(library_id_a, "resolve_room_conflict"))
    assert sink.all(library_id_b) == []
