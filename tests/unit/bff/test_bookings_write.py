from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.data.models import BookingRecord, BookingType
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import FakeAgentRuntimeClient
from bff.csrf import verify_csrf
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_repo
from bff.main import app
from bff.rate_limit import RateLimiter, get_case_creation_rate_limiter


@pytest.fixture
def wired():
    repo = InMemoryLibraryDataRepository()
    audit_sink = AuditLogSink()
    fake_client = FakeAgentRuntimeClient()

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="room_booking_staff", library_id="lib_demo", case_review_role=None
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_audit_sink] = lambda: audit_sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    yield TestClient(app), repo, audit_sink, fake_client
    app.dependency_overrides.clear()


def _body(**overrides):
    base = {
        "roomId": "room_a", "start": "2026-10-01T10:00:00+00:00", "end": "2026-10-01T11:00:00+00:00",
        "bookingType": "one_off_renter", "bookedBy": "patron_new_1",
    }
    base.update(overrides)
    return base


def test_creates_and_persists_the_new_booking(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/bookings", json=_body())
    assert response.status_code == 200
    booking_id = response.json()["bookingId"]
    assert repo.get_booking("lib_demo", booking_id) is not None


def test_no_conflict_returns_no_conflict_status_and_never_invokes_the_agent(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/bookings", json=_body())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_conflict"
    assert fake_client.calls == []


def test_an_overlapping_existing_booking_triggers_a_real_agent_invocation(wired):
    client, repo, audit_sink, fake_client = wired
    repo.save_booking(BookingRecord(
        booking_id="b_existing", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_existing", booking_type=BookingType.RECURRING_PROGRAM,
    ))
    response = client.post("/api/bookings", json=_body())
    assert response.status_code == 200
    booking_id = response.json()["bookingId"]

    assert len(fake_client.calls) == 1
    payload = fake_client.calls[0]
    assert payload["tool"] == "resolve_room_conflict"
    assert payload["library_id"] == "lib_demo"
    assert booking_id in payload["prompt"]
    assert "b_existing" in payload["prompt"]

    body = response.json()
    assert set(body["conflictingBookingIds"]) == {booking_id, "b_existing"}


def test_derives_library_id_from_claims_never_from_the_request_body(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/bookings", json={**_body(), "library_id": "some_other_library"})
    booking_id = response.json()["bookingId"]
    assert repo.get_booking("lib_demo", booking_id) is not None
    assert repo.get_booking("some_other_library", booking_id) is None


def test_writes_an_audit_event_for_the_creation_act(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/bookings", json=_body())
    booking_id = response.json()["bookingId"]
    matching = [r for r in audit_sink.all() if r.tool_name == "create_booking"]
    assert len(matching) == 1
    assert matching[0].tool_input["booking_id"] == booking_id
    assert matching[0].outcome == "created"


def test_returns_pending_approval_when_a_conflict_triggers_an_interrupt(wired):
    client, repo, audit_sink, fake_client = wired
    repo.save_booking(BookingRecord(
        booking_id="b_existing2", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_existing", booking_type=BookingType.RECURRING_PROGRAM,
    ))
    fake_client._response = {"status": "ok", "stop_reason": "interrupt", "tool_outcome": None}
    response = client.post("/api/bookings", json=_body())
    assert response.json()["status"] == "pending_approval"


def test_returns_resolved_only_when_tool_outcome_is_committed(wired):
    client, repo, audit_sink, fake_client = wired
    repo.save_booking(BookingRecord(
        booking_id="b_existing3", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_existing", booking_type=BookingType.RECURRING_PROGRAM,
    ))
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "committed"}
    response = client.post("/api/bookings", json=_body())
    assert response.json()["status"] == "resolved"


def test_invalid_room_id_returns_422(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/bookings", json=_body(roomId="room_nonexistent"))
    assert response.status_code == 422
    assert fake_client.calls == []


def test_agent_invocation_failure_deletes_the_orphaned_booking(wired):
    client, repo, audit_sink, fake_client = wired
    repo.save_booking(BookingRecord(
        booking_id="b_existing4", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_existing", booking_type=BookingType.RECURRING_PROGRAM,
    ))

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    fake_client.invoke = _raise
    response = client.post("/api/bookings", json=_body())
    assert response.json()["status"] == "agent_invocation_failed"
    booking_id = response.json()["bookingId"]
    assert repo.get_booking("lib_demo", booking_id) is None
    # The pre-existing conflicting booking must survive; only the new one is cleaned up
    assert repo.get_booking("lib_demo", "b_existing4") is not None


def test_a_naive_datetime_matching_the_real_html_form_still_detects_a_conflict(wired):
    # C1 (final review fix round): frontend/components/new-booking-form.tsx's
    # <input type="datetime-local"> produces exactly this naive shape (no
    # +00:00 suffix). Before the fix, comparing it against an existing
    # timezone-aware booking raised TypeError inside the repository's
    # overlap check -- reproduced live as a real 500. A 200 with a
    # non-no_conflict status here proves the overlap comparison actually
    # ran (and found the conflict) despite the naive input, not that the
    # crash was merely swallowed.
    client, repo, audit_sink, fake_client = wired
    repo.save_booking(BookingRecord(
        booking_id="b_existing_naive", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_existing", booking_type=BookingType.RECURRING_PROGRAM,
    ))
    response = client.post(
        "/api/bookings",
        json=_body(start="2026-10-01T10:00:00", end="2026-10-01T11:00:00"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"pending_approval", "resolved", "needs_attention"}


def test_an_inverted_range_is_rejected_with_422_and_never_invokes_the_agent(wired):
    # I1 (final review fix round): end before start must never be accepted
    # -- previously this returned 200/no_conflict and persisted a corrupt
    # booking.
    client, repo, audit_sink, fake_client = wired
    response = client.post(
        "/api/bookings",
        json=_body(start="2026-10-01T11:00:00+00:00", end="2026-10-01T10:00:00+00:00"),
    )
    assert response.status_code == 422
    assert fake_client.calls == []


def test_the_booking_creation_endpoint_trips_429_once_its_configured_limit_is_exceeded(wired):
    # I2: mirrors test_cases_write.py's own case-creation rate-limit test
    # pattern exactly -- this route shares the same dedicated limiter.
    client, repo, audit_sink, fake_client = wired
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_case_creation_rate_limiter] = lambda: limiter
    try:
        statuses = [client.post("/api/bookings", json=_body()).status_code for _ in range(3)]
    finally:
        app.dependency_overrides.pop(get_case_creation_rate_limiter, None)

    assert statuses == [200, 200, 429]


def test_creating_a_booking_without_a_csrf_cookie_or_header_is_rejected(wired):
    # I2: conftest.py's autouse fixture disables CSRF for every test in
    # this suite; this re-enables the real check for this one test,
    # mirroring test_cases_write.py's own pattern for the ILL endpoint.
    client, repo, audit_sink, fake_client = wired
    app.dependency_overrides.pop(verify_csrf, None)
    response = client.post("/api/bookings", json=_body())
    assert response.status_code == 403


def test_two_different_libraries_never_see_each_others_created_bookings(wired):
    client, repo, audit_sink, fake_client = wired
    first = client.post("/api/bookings", json=_body(bookedBy="lib_demo_patron"))
    lib_demo_booking_id = first.json()["bookingId"]

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="room_booking_staff", library_id="lib_other", case_review_role=None
    )
    second = client.get("/api/calendar")
    assert second.status_code == 200
    assert all(b["bookingId"] != lib_demo_booking_id for b in second.json())

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="room_booking_staff", library_id="lib_demo", case_review_role=None
    )
    third = client.get("/api/calendar")
    assert any(b["bookingId"] == lib_demo_booking_id for b in third.json())
