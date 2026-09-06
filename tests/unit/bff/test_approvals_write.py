import pytest
from fastapi.testclient import TestClient

from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink, PendingApprovalRecord
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import FakeAgentRuntimeClient
from bff.deps import get_agent_runtime_client, get_current_claims, get_pending_approvals_sink
from bff.main import app


def _red_record():
    return PendingApprovalRecord(
        library_id="lib_demo", case_id="b1:b2", tier="RED", tool="resolve_room_conflict",
        workflow="room_booking", reason={"tier": "RED"}, interrupt_id="v1:before_tool_call:xyz",
        session_id="sess_write_test", created_at="2026-09-06T00:00:00+00:00",
    )


def _yellow_record():
    return PendingApprovalRecord(
        library_id="lib_demo", case_id="ill_req_123", tier="YELLOW", tool="route_ill_request",
        workflow="ill_routing", reason={"tier": "YELLOW"}, interrupt_id="v1:before_tool_call:abc",
        session_id="sess_write_test_2", created_at="2026-09-06T00:00:00+00:00",
    )


@pytest.fixture
def wired(monkeypatch):
    sink = InMemoryPendingApprovalsSink()
    sink.put(_red_record())
    sink.put(_yellow_record())
    fake_client = FakeAgentRuntimeClient()

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    yield TestClient(app), sink, fake_client
    app.dependency_overrides.clear()


def test_approve_builds_the_correct_interrupt_response_payload_and_invokes_the_runtime(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    assert response.status_code == 200

    assert len(fake_client.calls) == 1
    payload = fake_client.calls[0]
    assert payload["session_id"] == "sess_write_test"
    assert payload["library_id"] == "lib_demo"
    prompt = payload["prompt"]
    assert prompt == [{"interruptResponse": {"interruptId": "v1:before_tool_call:xyz", "response": {
        "approved": True, "approver_role": "librarian_case_review", "token": "hitl_resume:b1:b2", "edited_value": None,
    }}}]


def test_approve_deletes_the_pending_approvals_row_on_success(wired):
    client, sink, fake_client = wired
    client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    # The wired fixture seeds two pending rows for lib_demo (b1:b2 and
    # ill_req_123) -- only the acted-upon case's row must be deleted.
    # Deleting the unrelated ill_req_123 row would itself be a bug.
    remaining_case_ids = {r.case_id for r in sink.list_for_library("lib_demo")}
    assert "b1:b2" not in remaining_case_ids
    assert "ill_req_123" in remaining_case_ids


def test_decline_submits_approved_false_and_still_deletes_the_row(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "decline", "declineReason": "Wrong candidate."})
    assert response.status_code == 200
    payload = fake_client.calls[0]
    assert payload["prompt"][0]["interruptResponse"]["response"]["approved"] is False
    # Same rationale as the approve test above: only the acted-upon case's
    # row is expected to be gone, not the unrelated ill_req_123 row.
    remaining_case_ids = {r.case_id for r in sink.list_for_library("lib_demo")}
    assert "b1:b2" not in remaining_case_ids
    assert "ill_req_123" in remaining_case_ids


def test_edit_includes_the_edited_value_in_the_response_payload(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "edit", "editedValue": "b2"})
    assert response.status_code == 200
    payload = fake_client.calls[0]
    assert payload["prompt"][0]["interruptResponse"]["response"]["edited_value"] == "b2"


def test_a_red_case_is_rejected_with_403_when_the_caller_has_no_case_review_role():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_red_record())
    fake_client = FakeAgentRuntimeClient()
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="circulation_staff", library_id="lib_demo", case_review_role=None
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    try:
        client = TestClient(app)
        response = client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert fake_client.calls == []
    # A rejected decision must not delete the pending row -- the case is
    # still genuinely waiting on a qualified human.
    assert sink.list_for_library("lib_demo") != []


def test_a_yellow_case_uses_the_callers_own_role_not_case_review_role(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/ill_req_123/decision", json={"action": "approve"})
    assert response.status_code == 200
    payload = fake_client.calls[0]
    assert payload["prompt"][0]["interruptResponse"]["response"]["approver_role"] == "branch_manager"


def test_decision_for_an_unknown_case_id_returns_404(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/no_such_case/decision", json={"action": "approve"})
    assert response.status_code == 404
