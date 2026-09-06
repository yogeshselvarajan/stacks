from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink, PendingApprovalRecord


def _record(library_id="lib_demo", case_id="b1:b2", **overrides):
    fields = dict(
        library_id=library_id, case_id=case_id, tier="RED", tool="resolve_room_conflict",
        workflow="room_booking", reason={"tier": "RED"}, interrupt_id="v1:before_tool_call:abc",
        session_id="sess_1", created_at="2026-09-06T00:00:00+00:00",
    )
    fields.update(overrides)
    return PendingApprovalRecord(**fields)


def test_put_then_list_for_library_returns_the_record():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_record())
    records = sink.list_for_library("lib_demo")
    assert len(records) == 1
    assert records[0].case_id == "b1:b2"
    assert records[0].interrupt_id == "v1:before_tool_call:abc"


def test_list_for_library_does_not_leak_across_library_id():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_record(library_id="lib_a", case_id="c1"))
    sink.put(_record(library_id="lib_b", case_id="c2"))
    assert [r.case_id for r in sink.list_for_library("lib_a")] == ["c1"]


def test_put_twice_for_the_same_case_overwrites_not_duplicates():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_record(tier="YELLOW"))
    sink.put(_record(tier="RED"))
    records = sink.list_for_library("lib_demo")
    assert len(records) == 1
    assert records[0].tier == "RED"


def test_delete_removes_the_record():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_record())
    sink.delete("lib_demo", "b1:b2")
    assert sink.list_for_library("lib_demo") == []


def test_delete_of_unknown_case_is_a_safe_no_op():
    sink = InMemoryPendingApprovalsSink()
    sink.delete("lib_demo", "no_such_case")  # must not raise
    assert sink.list_for_library("lib_demo") == []


def test_record_to_dict_round_trips_every_field():
    record = _record()
    as_dict = record.to_dict()
    assert as_dict == {
        "library_id": "lib_demo", "case_id": "b1:b2", "tier": "RED", "tool": "resolve_room_conflict",
        "workflow": "room_booking", "reason": {"tier": "RED"}, "interrupt_id": "v1:before_tool_call:abc",
        "session_id": "sess_1", "created_at": "2026-09-06T00:00:00+00:00",
    }
