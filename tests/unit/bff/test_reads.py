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
        audit_id="a1", tool_name="resolve_room_conflict",
        tool_input={"conflicting_booking_ids": ["b_walkin_b", "b_recurring_b"]}, tool_output_status="success",
        outcome="committed", session_id="s1", library_id="lib_demo", actor=AuditActor.AGENT, actor_identity=None,
        timestamp=datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(), hitl_tier="GREEN", notification_id=None,
    ))
    audit_sink.append(AuditLogRecord(
        audit_id="a2", tool_name="run_overdue_chase",
        tool_input={"circulation_record_id": "circ_red"}, tool_output_status="success",
        outcome="committed", session_id="s1", library_id="lib_demo", actor=AuditActor.AGENT, actor_identity=None,
        timestamp=datetime(2026, 9, 2, tzinfo=timezone.utc).isoformat(), hitl_tier="RED", notification_id=None,
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
    body = response.json()
    assert len(body) >= 1
    # roomName is a human-readable label alongside the raw roomId -- the
    # UI shows this instead of the bare "room_a" internal id.
    assert body[0]["roomName"] == "Story Room"


def test_get_audit_list_returns_entries_for_the_callers_library(wired_client):
    response = wired_client.get("/api/audit")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["toolName"] == "resolve_room_conflict"
    assert body[0]["hitlTier"] == "GREEN"


def test_get_ill_queue_returns_the_seeded_requests_for_the_callers_library(wired_client):
    response = wired_client.get("/api/ill-queue")
    assert response.status_code == 200
    body = response.json()
    ids = {r["illRequestId"] for r in body}
    assert ids == {"ill_unambiguous", "ill_ambiguous", "ill_open_1", "ill_open_2", "ill_open_3"}
    for r in body:
        assert r["tier"] is None  # no pending ill_routing approval seeded in this fixture
        assert r["specialistTrace"] is None
        assert r["recallSummary"] is None  # no memory dependency wired in this fixture


def test_get_ill_queue_surfaces_the_specialists_persisted_trace(wired_client):
    from bff.deps import get_repo
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    request = repo.get_ill_request("lib_demo", "ill_ambiguous")
    request.specialist_narrowed_candidate_id = "hold_2a"
    request.specialist_confidence = 0.82
    request.specialist_still_ambiguous = False
    repo.save_ill_request(request)
    app.dependency_overrides[get_repo] = lambda: repo

    response = wired_client.get("/api/ill-queue")
    body = {r["illRequestId"]: r for r in response.json()}
    assert body["ill_ambiguous"]["specialistTrace"] == {
        "narrowedCandidateId": "hold_2a", "confidence": 0.82, "stillAmbiguous": False,
    }
    assert body["ill_unambiguous"]["specialistTrace"] is None


def test_get_ill_queue_and_overdue_queue_surface_real_memory_recall(wired_client):
    from bff.deps import get_memory
    from stacks.types import HardshipHistoryFact, RequesterSubstitutionPattern

    class _FakeMemory:
        def get_ill_substitution_pattern(self, library_id, requester_key):
            return RequesterSubstitutionPattern(
                request_frequency=3, subject_areas=["fiction"],
                has_accepted_substitution_without_escalation=True,
                last_updated=datetime(2026, 8, 1, tzinfo=timezone.utc),
            )

        def get_hardship_history(self, library_id, patron_id):
            return HardshipHistoryFact(flagged_at=datetime(2026, 6, 1, tzinfo=timezone.utc))

    app.dependency_overrides[get_memory] = lambda: _FakeMemory()

    ill_body = wired_client.get("/api/ill-queue").json()
    assert all("accepted a substitute edition" in r["recallSummary"] for r in ill_body)

    overdue_body = wired_client.get("/api/overdue-queue").json()
    assert all("Hardship flag on file since 2026-06-01" in c["recallSummary"] for c in overdue_body)


def test_get_ill_queue_reports_the_pending_approvals_tier(wired_client):
    from bff.deps import get_pending_approvals_sink
    sink = InMemoryPendingApprovalsSink()
    sink.put(PendingApprovalRecord(
        library_id="lib_demo", case_id="ill_ambiguous", tier="YELLOW", tool="route_ill_request",
        workflow="ill_routing", reason={"tier": "YELLOW"}, interrupt_id="v1:y", session_id="sess_bff_test",
        created_at="2026-09-06T00:00:00+00:00",
    ))
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    response = wired_client.get("/api/ill-queue")
    body = {r["illRequestId"]: r for r in response.json()}
    assert body["ill_ambiguous"]["tier"] == "YELLOW"
    assert body["ill_unambiguous"]["tier"] is None


def test_get_ill_queue_never_returns_a_request_for_a_different_library(wired_client):
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_other", case_review_role="librarian_case_review"
    )
    response = wired_client.get("/api/ill-queue")
    assert response.json() == []


def test_get_overdue_queue_returns_the_seeded_overdue_records(wired_client):
    response = wired_client.get("/api/overdue-queue")
    assert response.status_code == 200
    body = {c["circulationRecordId"]: c for c in response.json()}
    assert set(body.keys()) == {"circ_green", "circ_red", "circ_003", "circ_004"}
    # circ_green has prior_reminder_tier_sent=-1: nothing sent yet, first
    # tier is pending (no PendingApprovals case seeded for it).
    assert body["circ_green"]["tierHistory"] == [{"tierIndex": 0, "label": "Informational", "status": "pending"}]
    # circ_red has prior_reminder_tier_sent=3: every ladder tier already sent.
    assert [step["status"] for step in body["circ_red"]["tierHistory"]] == ["sent", "sent", "sent", "sent"]
    # Every case surfaces a human-readable patron name and item title, not
    # just the raw internal ids -- the whole point of this fixture/BFF
    # enrichment.
    assert body["circ_green"]["patronName"] == "Maria Chen"
    assert body["circ_green"]["itemTitle"] == "The Great Gatsby"


def test_get_overdue_queue_marks_a_tier_with_a_pending_case_as_held_for_review(wired_client):
    from bff.deps import get_pending_approvals_sink
    sink = InMemoryPendingApprovalsSink()
    sink.put(PendingApprovalRecord(
        library_id="lib_demo", case_id="circ_green", tier="YELLOW", tool="run_overdue_chase",
        workflow="overdue_chase", reason={"tier": "YELLOW"}, interrupt_id="v1:z", session_id="sess_bff_test",
        created_at="2026-09-06T00:00:00+00:00",
    ))
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    response = wired_client.get("/api/overdue-queue")
    body = {c["circulationRecordId"]: c for c in response.json()}
    assert body["circ_green"]["tierHistory"][0]["status"] == "held_for_review"


def test_get_overdue_queue_never_returns_a_record_for_a_different_library(wired_client):
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_other", case_review_role="librarian_case_review"
    )
    response = wired_client.get("/api/overdue-queue")
    assert response.json() == []


def test_get_audit_trace_filters_to_the_matching_case_only(wired_client):
    response = wired_client.get("/api/audit/circ_red")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["toolName"] == "run_overdue_chase"


def test_get_audit_trace_room_conflict_case_matches_the_sorted_booking_ids(wired_client):
    response = wired_client.get("/api/audit/b_recurring_b:b_walkin_b")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["toolName"] == "resolve_room_conflict"


def test_get_audit_trace_returns_empty_for_an_unmatched_case_id(wired_client):
    response = wired_client.get("/api/audit/no_such_case")
    assert response.json() == []


def test_reads_require_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.get("/api/approvals")
    assert response.status_code == 401
