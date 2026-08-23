from stacks.hooks.audit_log import AuditLogHook, AuditLogSink


class _FakeToolUse(dict):
    pass


class _FakeAfterEvent:
    def __init__(self, tool_name: str, tool_input: dict, result: dict, exception=None):
        self.tool_use = _FakeToolUse(name=tool_name, input=tool_input)
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
