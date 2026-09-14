import pytest
from fastapi.testclient import TestClient

from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import FakeAgentRuntimeClient
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_repo
from bff.main import app


@pytest.fixture
def wired():
    repo = InMemoryLibraryDataRepository()
    audit_sink = AuditLogSink()
    fake_client = FakeAgentRuntimeClient()

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="ill_coordinator", library_id="lib_demo", case_review_role=None
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_audit_sink] = lambda: audit_sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    yield TestClient(app), repo, audit_sink, fake_client
    app.dependency_overrides.clear()


def _body(**overrides):
    base = {"requestedTitle": "The Left Hand of Darkness", "requesterPatronId": "patron_new_1"}
    base.update(overrides)
    return base


def test_creates_and_persists_a_new_open_ill_request(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/ill-requests", json=_body())
    assert response.status_code == 200
    body = response.json()
    ill_request_id = body["illRequestId"]
    assert ill_request_id.startswith("ill_")

    stored = repo.get_ill_request("lib_demo", ill_request_id)
    assert stored is not None
    assert stored.requested_title == "The Left Hand of Darkness"
    assert stored.requester_patron_id == "patron_new_1"
    assert stored.status.value == "open"


def test_derives_library_id_from_claims_never_from_the_request_body(wired):
    client, repo, audit_sink, fake_client = wired
    # CreateIllRequestBody has no library_id field at all -- passing one is
    # simply ignored by pydantic, proving the client cannot influence tenant
    # scoping even if it tries.
    response = client.post("/api/ill-requests", json={**_body(), "library_id": "some_other_library"})
    assert response.status_code == 200
    ill_request_id = response.json()["illRequestId"]
    assert repo.get_ill_request("lib_demo", ill_request_id) is not None
    assert repo.get_ill_request("some_other_library", ill_request_id) is None


def test_writes_an_audit_event_for_the_creation_act(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/ill-requests", json=_body())
    ill_request_id = response.json()["illRequestId"]

    matching = [r for r in audit_sink.all() if r.tool_name == "create_ill_request"]
    assert len(matching) == 1
    record = matching[0]
    assert record.library_id == "lib_demo"
    assert record.outcome == "created"
    assert record.actor.value == "HUMAN"
    assert record.tool_input["ill_request_id"] == ill_request_id


def test_invokes_the_real_agent_with_a_prompt_naming_the_new_case(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/ill-requests", json=_body())
    ill_request_id = response.json()["illRequestId"]

    assert len(fake_client.calls) == 1
    payload = fake_client.calls[0]
    assert payload["library_id"] == "lib_demo"
    assert payload["role"] == "ill_coordinator"
    assert ill_request_id in payload["prompt"]


def test_returns_pending_approval_when_the_agent_interrupts(wired):
    client, repo, audit_sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "interrupt", "tool_outcome": None}
    response = client.post("/api/ill-requests", json=_body())
    assert response.status_code == 200
    assert response.json()["status"] == "pending_approval"


def test_returns_resolved_when_the_agent_commits_without_interrupt(wired):
    client, repo, audit_sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "committed"}
    response = client.post("/api/ill-requests", json=_body())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["outcome"] == "committed"


def test_rejects_an_empty_title_with_422_and_never_invokes_the_agent(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/ill-requests", json=_body(requestedTitle=""))
    assert response.status_code == 422
    assert fake_client.calls == []


def test_two_different_libraries_never_see_each_others_created_requests(wired):
    client, repo, audit_sink, fake_client = wired
    first = client.post("/api/ill-requests", json=_body(requestedTitle="Lib Demo's Own Book"))
    lib_demo_id = first.json()["illRequestId"]

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="ill_coordinator", library_id="lib_other", case_review_role=None
    )
    second = client.get("/api/ill-queue")
    assert second.status_code == 200
    assert all(r["illRequestId"] != lib_demo_id for r in second.json())

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="ill_coordinator", library_id="lib_demo", case_review_role=None
    )
    third = client.get("/api/ill-queue")
    assert any(r["illRequestId"] == lib_demo_id for r in third.json())
