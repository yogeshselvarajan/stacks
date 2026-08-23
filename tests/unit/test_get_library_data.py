from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.tools.get_library_data import make_get_library_data


def _repo():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return repo


def test_room_calendar_query_returns_bookings():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(
        library_id="lib_demo", query_type="room_calendar",
        room_calendar_filter={"room_id": "room_a", "start": "2026-09-01T00:00:00+00:00", "end": "2026-09-02T00:00:00+00:00"},
    )
    assert result["status"] == "success"
    bookings = result["content"][0]["json"]["bookings"]
    assert len(bookings) == 2


def test_room_calendar_filter_missing_start_and_end_returns_invalid_filter():
    """A room_calendar_filter with only room_id (no start/end keys at all)
    must degrade to the invalid_filter error response, not raise a
    KeyError -- whole-branch review Minor 8."""
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", query_type="room_calendar", room_calendar_filter={"room_id": "room_a"})
    assert result["status"] == "error"
    assert "invalid_filter" in result["content"][0]["text"]


def test_cross_tenant_query_is_denied():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(
        library_id="lib_other", query_type="room_calendar",
        room_calendar_filter={"room_id": "room_a", "start": "2026-09-01T00:00:00+00:00", "end": "2026-09-02T00:00:00+00:00"},
    )
    assert result["status"] == "error"
    assert "cross_tenant_denied" in result["content"][0]["text"]


def test_ill_queue_query_not_found_is_distinct_from_missing_filter():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    not_found = tool_fn(library_id="lib_demo", query_type="ill_queue", ill_queue_filter={"ill_request_id": "does_not_exist"})
    assert not_found["status"] == "error"
    assert "not_found" in not_found["content"][0]["text"]

    missing_filter = tool_fn(library_id="lib_demo", query_type="ill_queue")
    assert missing_filter["status"] == "error"
    assert "invalid_filter" in missing_filter["content"][0]["text"]


def test_policy_document_query_returns_clauses():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", query_type="policy_document", policy_filter={"policy_name": "room_booking_priority"})
    assert result["status"] == "success"
    clauses = result["content"][0]["json"]["clauses"]
    assert clauses[0]["clause_id"] == "RBP-1"


def test_invalid_query_type_is_rejected():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", query_type="patron_search")
    assert result["status"] == "error"
    assert "invalid_query_type" in result["content"][0]["text"]


def test_circulation_record_query_returns_record():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", query_type="circulation_record", circulation_filter={"circulation_record_id": "circ_green"})
    assert result["status"] == "success"
    record = result["content"][0]["json"]["record"]
    assert record["circulation_record_id"] == "circ_green"


def test_circulation_record_query_not_found():
    tool_fn = make_get_library_data(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", query_type="circulation_record", circulation_filter={"circulation_record_id": "does_not_exist"})
    assert result["status"] == "error"
    assert "not_found" in result["content"][0]["text"]
