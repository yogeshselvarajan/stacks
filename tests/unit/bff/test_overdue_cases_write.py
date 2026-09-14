from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims
from stacks.types import SensitivityFlag

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
        role="circulation_staff", library_id="lib_demo", case_review_role=None
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_audit_sink] = lambda: audit_sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: fake_client
    yield TestClient(app), repo, audit_sink, fake_client
    app.dependency_overrides.clear()


def _body(**overrides):
    base = {"patronId": "patron_new_1", "itemId": "item_new_1", "itemType": "book", "daysOverdue": 5}
    base.update(overrides)
    return base


def test_creates_and_persists_a_new_overdue_circulation_record(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json=_body())
    assert response.status_code == 200
    body = response.json()
    circulation_record_id = body["circulationRecordId"]
    assert circulation_record_id.startswith("circ_")

    stored = repo.get_circulation_record("lib_demo", circulation_record_id)
    assert stored is not None
    assert stored.patron_id == "patron_new_1"
    assert stored.item_id == "item_new_1"
    assert stored.prior_reminder_tier_sent == -1

    now = datetime.now(timezone.utc)
    expected_due = now - timedelta(days=5)
    assert abs((stored.due_date - expected_due).total_seconds()) < 60


def test_derives_library_id_from_claims_never_from_the_request_body(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json={**_body(), "library_id": "some_other_library"})
    assert response.status_code == 200
    circulation_record_id = response.json()["circulationRecordId"]
    assert repo.get_circulation_record("lib_demo", circulation_record_id) is not None
    assert repo.get_circulation_record("some_other_library", circulation_record_id) is None


def test_sensitivity_flag_true_sets_minor_account_flag_on_the_record(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json=_body(sensitivityFlag=True))
    circulation_record_id = response.json()["circulationRecordId"]
    stored = repo.get_circulation_record("lib_demo", circulation_record_id)
    assert stored.flags == [SensitivityFlag.MINOR_ACCOUNT]


def test_writes_an_audit_event_for_the_creation_act(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json=_body())
    circulation_record_id = response.json()["circulationRecordId"]

    matching = [r for r in audit_sink.all() if r.tool_name == "create_overdue_case"]
    assert len(matching) == 1
    record = matching[0]
    assert record.library_id == "lib_demo"
    assert record.outcome == "created"
    assert record.actor.value == "HUMAN"
    assert record.tool_input["circulation_record_id"] == circulation_record_id


def test_invokes_the_real_agent_with_a_prompt_naming_the_new_case_and_the_tool_key(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json=_body())
    circulation_record_id = response.json()["circulationRecordId"]

    assert len(fake_client.calls) == 1
    payload = fake_client.calls[0]
    assert payload["library_id"] == "lib_demo"
    assert payload["role"] == "circulation_staff"
    assert payload["tool"] == "run_overdue_chase"
    assert circulation_record_id in payload["prompt"]


def test_returns_pending_approval_when_the_agent_interrupts(wired):
    client, repo, audit_sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "interrupt", "tool_outcome": None}
    response = client.post("/api/overdue-cases", json=_body())
    assert response.json()["status"] == "pending_approval"


def test_returns_resolved_only_when_tool_outcome_is_committed(wired):
    client, repo, audit_sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "committed"}
    response = client.post("/api/overdue-cases", json=_body())
    body = response.json()
    assert body["status"] == "resolved"
    assert body["outcome"] == "committed"


def test_returns_needs_attention_when_the_tool_outcome_is_not_committed(wired):
    client, repo, audit_sink, fake_client = wired
    fake_client._response = {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "blocked_missing_approval"}
    response = client.post("/api/overdue-cases", json=_body())
    body = response.json()
    assert body["status"] == "needs_attention"
    assert body["outcome"] == "blocked_missing_approval"


def test_rejects_a_non_positive_days_overdue_with_422_and_never_invokes_the_agent(wired):
    client, repo, audit_sink, fake_client = wired
    response = client.post("/api/overdue-cases", json=_body(daysOverdue=0))
    assert response.status_code == 422
    assert fake_client.calls == []


def test_agent_invocation_failure_deletes_the_orphaned_record(monkeypatch, wired):
    client, repo, audit_sink, fake_client = wired

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    fake_client.invoke = _raise
    response = client.post("/api/overdue-cases", json=_body())
    assert response.json()["status"] == "agent_invocation_failed"
    circulation_record_id = response.json()["circulationRecordId"]
    assert repo.get_circulation_record("lib_demo", circulation_record_id) is None


def test_the_overdue_case_creation_endpoint_trips_429_once_its_configured_limit_is_exceeded(wired):
    # I2: mirrors test_cases_write.py's own case-creation rate-limit test
    # pattern exactly -- this route shares the same dedicated limiter.
    client, repo, audit_sink, fake_client = wired
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_case_creation_rate_limiter] = lambda: limiter
    try:
        statuses = [client.post("/api/overdue-cases", json=_body()).status_code for _ in range(3)]
    finally:
        app.dependency_overrides.pop(get_case_creation_rate_limiter, None)

    assert statuses == [200, 200, 429]


def test_creating_an_overdue_case_without_a_csrf_cookie_or_header_is_rejected(wired):
    # I2: conftest.py's autouse fixture disables CSRF for every test in
    # this suite; this re-enables the real check for this one test,
    # mirroring test_cases_write.py's own pattern for the ILL endpoint.
    client, repo, audit_sink, fake_client = wired
    app.dependency_overrides.pop(verify_csrf, None)
    response = client.post("/api/overdue-cases", json=_body())
    assert response.status_code == 403


def test_two_different_libraries_never_see_each_others_created_overdue_cases(wired):
    client, repo, audit_sink, fake_client = wired
    first = client.post("/api/overdue-cases", json=_body(patronId="lib_demo_patron"))
    lib_demo_record_id = first.json()["circulationRecordId"]

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="circulation_staff", library_id="lib_other", case_review_role=None
    )
    second = client.get("/api/overdue-queue")
    assert second.status_code == 200
    assert all(c["circulationRecordId"] != lib_demo_record_id for c in second.json())

    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="circulation_staff", library_id="lib_demo", case_review_role=None
    )
    third = client.get("/api/overdue-queue")
    assert any(c["circulationRecordId"] == lib_demo_record_id for c in third.json())
