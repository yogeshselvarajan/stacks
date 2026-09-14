import pytest
from fastapi.testclient import TestClient

from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import FakeAgentRuntimeClient
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_pending_approvals_sink, get_repo
from bff.main import app


def _client_as(role: str, case_review_role: str | None = None) -> TestClient:
    repo = InMemoryLibraryDataRepository()
    audit_sink = AuditLogSink()
    approvals_sink = InMemoryPendingApprovalsSink()
    fake_client = FakeAgentRuntimeClient()

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role=role, library_id="lib_demo", case_review_role=case_review_role
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_audit_sink] = lambda: audit_sink
    app.dependency_overrides[get_pending_approvals_sink] = lambda: approvals_sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _booking_body(**overrides):
    base = {
        "roomId": "room_a", "start": "2026-10-01T10:00:00+00:00", "end": "2026-10-01T11:00:00+00:00",
        "bookingType": "one_off_renter", "bookedBy": "patron_x",
    }
    base.update(overrides)
    return base


def _overdue_body(**overrides):
    base = {"patronId": "patron_x", "itemId": "item_x", "itemType": "book", "daysOverdue": 5}
    base.update(overrides)
    return base


def _ill_body(**overrides):
    base = {"requestedTitle": "Some Book", "requesterPatronId": "patron_x"}
    base.update(overrides)
    return base


def test_calendar_read_rejects_ill_coordinator():
    client = _client_as("ill_coordinator")
    response = client.get("/api/calendar")
    assert response.status_code == 403


def test_calendar_read_allows_room_booking_staff():
    client = _client_as("room_booking_staff")
    response = client.get("/api/calendar")
    assert response.status_code == 200


def test_calendar_read_allows_branch_manager():
    client = _client_as("branch_manager")
    response = client.get("/api/calendar")
    assert response.status_code == 200


def test_booking_creation_rejects_circulation_staff():
    client = _client_as("circulation_staff")
    response = client.post("/api/bookings", json=_booking_body())
    assert response.status_code == 403


def test_booking_creation_allows_room_booking_staff():
    client = _client_as("room_booking_staff")
    response = client.post("/api/bookings", json=_booking_body())
    assert response.status_code == 200


def test_ill_queue_read_rejects_circulation_staff():
    client = _client_as("circulation_staff")
    response = client.get("/api/ill-queue")
    assert response.status_code == 403


def test_ill_queue_read_allows_ill_coordinator():
    client = _client_as("ill_coordinator")
    response = client.get("/api/ill-queue")
    assert response.status_code == 200


def test_ill_request_creation_rejects_room_booking_staff():
    client = _client_as("room_booking_staff")
    response = client.post("/api/ill-requests", json=_ill_body())
    assert response.status_code == 403


def test_ill_request_creation_allows_branch_manager():
    client = _client_as("branch_manager")
    response = client.post("/api/ill-requests", json=_ill_body())
    assert response.status_code == 200


def test_overdue_queue_read_rejects_room_booking_staff():
    client = _client_as("room_booking_staff")
    response = client.get("/api/overdue-queue")
    assert response.status_code == 403


def test_overdue_queue_read_allows_circulation_staff():
    client = _client_as("circulation_staff")
    response = client.get("/api/overdue-queue")
    assert response.status_code == 200


def test_overdue_case_creation_rejects_ill_coordinator():
    client = _client_as("ill_coordinator")
    response = client.post("/api/overdue-cases", json=_overdue_body())
    assert response.status_code == 403


def test_overdue_case_creation_allows_branch_manager():
    client = _client_as("branch_manager")
    response = client.post("/api/overdue-cases", json=_overdue_body())
    assert response.status_code == 200


def test_approvals_read_rejects_a_role_with_no_case_review_role():
    client = _client_as("room_booking_staff", case_review_role=None)
    response = client.get("/api/approvals")
    assert response.status_code == 403


def test_approvals_read_allows_a_role_with_case_review_role_set():
    client = _client_as("circulation_staff", case_review_role="librarian_case_review")
    response = client.get("/api/approvals")
    assert response.status_code == 200


def test_approvals_read_allows_branch_manager_regardless_of_case_review_role():
    client = _client_as("branch_manager", case_review_role=None)
    response = client.get("/api/approvals")
    assert response.status_code == 200
