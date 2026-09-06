# tests/unit/bff/test_reads.py
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink, PendingApprovalRecord
from stacks.hooks.audit_log import AuditLogSink, AuditLogRecord
from stacks.identity.claims import StaffIdentityClaims
from stacks.types import AuditActor

from bff.deps import get_current_claims, get_pending_approvals_sink, get_repo, get_audit_sink
from bff.main import app


@pytest.fixture
def wired_client():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    pending_sink = InMemoryPendingApprovalsSink()
    pending_sink.put(PendingApprovalRecord(
        library_id="lib_demo", case_id="b_recurring_b:b_walkin_b", tier="RED", tool="resolve_room_conflict",
        workflow="room_booking", reason={"tier": "RED"}, interrupt_id="v1:x", session_id="sess_bff_test",
        created_at="2026-09-06T00:00:00+00:00",
    ))
    audit_sink = AuditLogSink()
    audit_sink.append(AuditLogRecord(
        audit_id="a1", tool_name="resolve_room_conflict", tool_input={}, tool_output_status="success",
        outcome="committed", session_id="s1", library_id="lib_demo", actor=AuditActor.AGENT, actor_identity=None,
        timestamp=datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(), hitl_tier="GREEN", notification_id=None,
    ))

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_pending_approvals_sink] = lambda: pending_sink
    app.dependency_overrides[get_audit_sink] = lambda: audit_sink
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_get_approvals_returns_the_pending_case_scoped_to_the_callers_library(wired_client):
    response = wired_client.get("/api/approvals")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["caseId"] == "b_recurring_b:b_walkin_b"
    assert body[0]["tier"] == "RED"
    assert body[0]["workflow"] == "room_booking"


def test_get_approvals_never_returns_a_case_for_a_different_library(wired_client):
    from bff.deps import get_current_claims
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_other", case_review_role="librarian_case_review"
    )
    response = wired_client.get("/api/approvals")
    assert response.json() == []


def test_get_calendar_returns_bookings_for_the_callers_library(wired_client):
    response = wired_client.get("/api/calendar?room_id=room_a")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_audit_list_returns_entries_for_the_callers_library(wired_client):
    response = wired_client.get("/api/audit")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["toolName"] == "resolve_room_conflict"
    assert body[0]["hitlTier"] == "GREEN"


def test_reads_require_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.get("/api/approvals")
    assert response.status_code == 401
