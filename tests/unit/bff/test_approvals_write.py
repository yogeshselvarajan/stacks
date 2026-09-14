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
    # A decline resumes into HitlGateHook's own cancel_tool path -- the
    # tool never commits. Override the shared fixture's "committed"
    # default (meant for approve/edit) with the realistic decline outcome.
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "blocked_missing_approval"}
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


# --- Task 17 fix round: I1 and I2 ---

def _overdue_record():
    return PendingApprovalRecord(
        library_id="lib_demo", case_id="circ_1", tier="YELLOW", tool="run_overdue_chase",
        workflow="overdue_chase", reason={"tier": "YELLOW"}, interrupt_id="v1:before_tool_call:def",
        session_id="sess_write_test_3", created_at="2026-09-06T00:00:00+00:00",
    )


def test_edit_with_no_edited_value_returns_400_and_never_invokes_the_runtime(wired):
    client, sink, fake_client = wired
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "edit"})
    assert response.status_code == 400
    assert fake_client.calls == []
    assert any(r.case_id == "b1:b2" for r in sink.list_for_library("lib_demo"))


def test_edit_for_a_workflow_with_no_editable_field_returns_400(monkeypatch):
    sink = InMemoryPendingApprovalsSink()
    sink.put(_overdue_record())
    fake_client = FakeAgentRuntimeClient()
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    try:
        client = TestClient(app)
        response = client.post("/api/approvals/circ_1/decision", json={"action": "edit", "editedValue": "new message"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert fake_client.calls == []


def test_approve_that_does_not_actually_commit_keeps_the_row_and_returns_an_error(wired):
    client, sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "blocked_missing_approval"}
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    assert response.status_code == 502
    assert any(r.case_id == "b1:b2" for r in sink.list_for_library("lib_demo"))


def test_a_resume_that_is_still_paused_keeps_the_row_and_returns_an_error(wired):
    client, sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "interrupt", "tool_outcome": None}
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    assert response.status_code == 502
    assert any(r.case_id == "b1:b2" for r in sink.list_for_library("lib_demo"))


def test_a_decline_that_unexpectedly_commits_keeps_the_row_and_returns_an_error(wired):
    client, sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "committed"}
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "decline"})
    assert response.status_code == 500
    assert any(r.case_id == "b1:b2" for r in sink.list_for_library("lib_demo"))


def test_approve_of_a_genuine_no_match_ill_case_succeeds_and_deletes_the_row(wired):
    # Live-observed, 2026-09-14: route_ill_request's own commit path
    # correctly records "no_match_recorded" as a terminal outcome when
    # its catalog search finds zero candidates -- there is no id left to
    # commit to. Before this fix, this endpoint treated anything other
    # than the literal string "committed" as a failed resume, so a
    # genuinely successful ILL no-match approval 502'd on a real,
    # already-resolved case.
    client, sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "no_match_recorded"}
    response = client.post("/api/approvals/ill_req_123/decision", json={"action": "approve"})
    assert response.status_code == 200
    assert "ill_req_123" not in {r.case_id for r in sink.list_for_library("lib_demo")}


def test_approve_that_hits_an_idempotent_already_committed_replay_still_succeeds(wired):
    client, sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "already_committed"}
    response = client.post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    assert response.status_code == 200
    assert "b1:b2" not in {r.case_id for r in sink.list_for_library("lib_demo")}
