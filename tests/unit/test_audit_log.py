from unittest import mock

from stacks.hooks.audit_log import AuditLogHook, AuditLogSink
from stacks.types import AuditActor


class _FakeToolUse(dict):
    pass


class _FakeAfterEvent:
    def __init__(self, tool_name: str, tool_input: dict, result: dict, exception=None, tool_use_id: str = "tu_123"):
        self.tool_use = _FakeToolUse(name=tool_name, input=tool_input, toolUseId=tool_use_id)
        self.result = result
        self.exception = exception


def test_mutating_tool_call_produces_exactly_one_record():
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")
    event = _FakeAfterEvent(
        "resolve_room_conflict",
        {"action": "commit", "conflicting_booking_ids": ["b1", "b2"], "rationale": "should not appear in audit log"},
        {"status": "success", "content": [{"json": {}}]},
    )
    hook._record(event)
    records = sink.all()
    assert len(records) == 1
    assert records[0].tool_name == "resolve_room_conflict"
    assert records[0].tool_output_status == "success"


def test_read_only_tool_calls_are_not_audited():
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")
    event = _FakeAfterEvent("get_library_data", {"query_type": "room_calendar"}, {"status": "success", "content": []})
    hook._record(event)
    assert sink.all() == []


def test_sensitive_fields_are_stripped_from_the_logged_input():
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")
    event = _FakeAfterEvent(
        "run_overdue_chase",
        {"action": "commit", "circulation_record_id": "circ_1", "message_body": "Dear patron, your account has a hardship note..."},
        {"status": "success", "content": [{"json": {}}]},
    )
    hook._record(event)
    logged_input = sink.all()[0].tool_input
    assert "message_body" not in logged_input
    assert logged_input["circulation_record_id"] == "circ_1"


def test_exception_is_recorded_as_error_status():
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")
    event = _FakeAfterEvent("notify_parties", {"related_action_id": "x"}, {"status": "error", "content": []}, exception=RuntimeError("boom"))
    hook._record(event)
    assert sink.all()[0].tool_output_status == "error"


def test_every_record_gets_a_monotonic_sequence_number():
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")
    for _ in range(3):
        hook._record(_FakeAfterEvent("notify_parties", {"related_action_id": "x"}, {"status": "success", "content": []}))
    sequences = [r.sequence for r in sink.all()]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == 3


def test_outcome_distinguishes_blocked_from_committed():
    """Outcome captures the true result from nested JSON, not just envelope status."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    # Real committed outcome
    event_committed = _FakeAfterEvent(
        "resolve_room_conflict",
        {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
        {"status": "success", "content": [{"json": {"status": "committed"}}]},
    )
    hook._record(event_committed)

    # Blocked outcome (still envelope status: success, but inner status is blocked_missing_approval)
    event_blocked = _FakeAfterEvent(
        "resolve_room_conflict",
        {"action": "commit", "conflicting_booking_ids": ["b3", "b4"]},
        {"status": "success", "content": [{"json": {"status": "blocked_missing_approval"}}]},
    )
    hook._record(event_blocked)

    records = sink.all()
    assert len(records) == 2
    assert records[0].tool_output_status == "success"  # envelope
    assert records[0].outcome == "committed"           # true outcome
    assert records[1].tool_output_status == "success"  # envelope
    assert records[1].outcome == "blocked_missing_approval"  # true outcome


def test_sink_append_exception_preserves_tool_use_id_and_logs():
    """If audit write fails, error result preserves toolUseId and logs exception."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    # Mock sink to raise on append
    with mock.patch.object(sink, "append", side_effect=RuntimeError("audit db down")):
        with mock.patch("stacks.hooks.audit_log.logger") as mock_logger:
            event = _FakeAfterEvent(
                "resolve_room_conflict",
                {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
                {"status": "success", "content": [{"json": {"status": "committed"}}]},
                tool_use_id="tu_xyz",
            )
            hook._record(event)

            # Verify logger.exception was called
            mock_logger.exception.assert_called_once_with("audit_write_failed")

            # Verify event.result was rewritten with toolUseId preserved
            assert event.result["status"] == "error"
            assert event.result["toolUseId"] == "tu_xyz"
            assert "audit_write_failed" in event.result["content"][0]["text"]


def test_approval_token_raw_value_never_logged():
    """Approval token's raw token string is stripped; only approver_role and related_action_id remain."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    event = _FakeAfterEvent(
        "resolve_room_conflict",
        {
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {
                "token": "secret_raw_jwt_token_xyz",
                "approver_role": "librarian_case_review",
                "related_action_id": "act_123",
            },
        },
        {"status": "success", "content": [{"json": {"status": "committed"}}]},
    )
    hook._record(event)

    record = sink.all()[0]
    logged_input = record.tool_input
    assert "token" not in logged_input.get("approval_token", {})
    assert logged_input["approval_token"]["approver_role"] == "librarian_case_review"
    assert logged_input["approval_token"]["related_action_id"] == "act_123"
    # Verify the raw token never appears anywhere in the serialized record
    serialized = str(record.to_dict())
    assert "secret_raw_jwt_token_xyz" not in serialized


def test_human_approved_commit_records_actor_as_human():
    """When approval_token with approver_role is present, actor is HUMAN."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    event = _FakeAfterEvent(
        "resolve_room_conflict",
        {
            "action": "commit",
            "conflicting_booking_ids": ["b1", "b2"],
            "approval_token": {
                "token": "secret_token",
                "approver_role": "librarian_case_review",
                "related_action_id": "act_123",
            },
        },
        {"status": "success", "content": [{"json": {"status": "committed"}}]},
    )
    hook._record(event)

    record = sink.all()[0]
    assert record.actor == AuditActor.HUMAN
    assert record.actor_identity == "librarian_case_review"


def test_agent_originated_commit_records_actor_as_agent():
    """When no approval_token is present, actor is AGENT."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    event = _FakeAfterEvent(
        "resolve_room_conflict",
        {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
        {"status": "success", "content": [{"json": {"status": "committed"}}]},
    )
    hook._record(event)

    record = sink.all()[0]
    assert record.actor == AuditActor.AGENT
    assert record.actor_identity is None


def test_outcome_falls_back_to_status_on_malformed_result():
    """If nested JSON is missing, outcome falls back to the envelope status."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    # Malformed result: no nested json
    event = _FakeAfterEvent(
        "resolve_room_conflict",
        {"action": "commit", "conflicting_booking_ids": ["b1", "b2"]},
        {"status": "success", "content": []},
    )
    hook._record(event)

    record = sink.all()[0]
    assert record.outcome == "success"  # Falls back to envelope status


def test_audit_log_input_deepcopy_prevents_aliasing():
    """Sanitized input is deeply copied so audit record doesn't hold live references."""
    sink = AuditLogSink()
    hook = AuditLogHook(sink, session_id="sess_1", library_id="lib_demo")

    # Create mutable list in input
    mutable_list = ["b1", "b2"]
    input_dict = {
        "action": "commit",
        "conflicting_booking_ids": mutable_list,
    }

    event = _FakeAfterEvent(
        "resolve_room_conflict",
        input_dict,
        {"status": "success", "content": [{"json": {"status": "committed"}}]},
    )
    hook._record(event)

    # Mutate the original list
    mutable_list.append("b3")

    # Audit record should have the original list, not the mutated one
    record = sink.all()[0]
    assert record.tool_input["conflicting_booking_ids"] == ["b1", "b2"]
