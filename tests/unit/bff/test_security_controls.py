# tests/unit/bff/test_security_controls.py
"""Closes the gap security.md Section 10.3 names explicitly: none of the
CSRF, CORS, or rate-limit controls it specifies had any test coverage.
Session-cookie attributes (httpOnly/Secure/SameSite) already have
coverage in test_auth.py; this file adds the remaining three.

conftest.py's autouse _permissive_security_controls fixture neutralizes
CSRF and rate limiting for every other test in this suite -- each test
below explicitly re-enables the real control it is testing (by popping
or overriding that one dependency) rather than relying on the permissive
default, then restores it in a finally block so later tests are
unaffected.
"""
from fastapi.testclient import TestClient

from stacks.hitl.pending_approvals import InMemoryPendingApprovalsSink, PendingApprovalRecord
from stacks.hooks.audit_log import AuditLogSink
from stacks.identity.claims import StaffIdentityClaims

from bff.clients.agent_runtime import FakeAgentRuntimeClient
from bff.config import SESSION_COOKIE_NAME
from bff.csrf import CSRF_COOKIE_NAME, verify_csrf
from bff.deps import get_agent_runtime_client, get_audit_sink, get_current_claims, get_pending_approvals_sink
from bff.main import app
from bff.rate_limit import RateLimiter, get_approval_rate_limiter, get_read_rate_limiter


def _red_record():
    return PendingApprovalRecord(
        library_id="lib_demo", case_id="b1:b2", tier="RED", tool="resolve_room_conflict",
        workflow="room_booking", reason={"tier": "RED"}, interrupt_id="v1:before_tool_call:xyz",
        session_id="sess_security_test", created_at="2026-09-06T00:00:00+00:00",
    )


# --- 8.4 CORS ---

def test_cors_reflects_the_configured_frontend_origin(client):
    response = client.get("/api/session", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_does_not_allow_an_arbitrary_cross_site_origin(client):
    response = client.get("/api/session", headers={"Origin": "https://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") is None


# --- 8.2 CSRF double-submit ---

def test_login_issues_a_readable_csrf_cookie_alongside_the_httponly_session_cookie(client):
    from unittest.mock import patch

    fake_cognito_response = {
        "AuthenticationResult": {"IdToken": "fake.id.token", "AccessToken": "fake.access.token", "ExpiresIn": 3600, "TokenType": "Bearer"}
    }
    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.return_value = fake_cognito_response
        response = client.post("/api/auth/login", json={"username": "u", "password": "p"})

    set_cookie_headers = [v.decode() for k, v in response.headers.raw if k == b"set-cookie"]
    csrf_cookie = next(h for h in set_cookie_headers if h.startswith(f"{CSRF_COOKIE_NAME}="))
    assert "HttpOnly" not in csrf_cookie  # the frontend must be able to read it
    assert "Secure" in csrf_cookie
    assert "SameSite=Strict" in csrf_cookie


def test_decision_without_a_csrf_cookie_or_header_is_rejected():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_red_record())
    app.dependency_overrides.pop(verify_csrf, None)  # re-enable the real check for this test
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: FakeAgentRuntimeClient()
    try:
        response = TestClient(app).post("/api/approvals/b1:b2/decision", json={"action": "approve"})
    finally:
        app.dependency_overrides.pop(get_current_claims, None)
        app.dependency_overrides.pop(get_pending_approvals_sink, None)
        app.dependency_overrides.pop(get_agent_runtime_client, None)

    assert response.status_code == 403


def test_decision_with_a_csrf_header_that_does_not_match_the_cookie_is_rejected():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_red_record())
    app.dependency_overrides.pop(verify_csrf, None)
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: FakeAgentRuntimeClient()
    try:
        test_client = TestClient(app)
        test_client.cookies.set(CSRF_COOKIE_NAME, "cookie-value")
        response = test_client.post(
            "/api/approvals/b1:b2/decision", json={"action": "approve"},
            headers={"X-Stacks-CSRF-Token": "a-different-value"},
        )
    finally:
        app.dependency_overrides.pop(get_current_claims, None)
        app.dependency_overrides.pop(get_pending_approvals_sink, None)
        app.dependency_overrides.pop(get_agent_runtime_client, None)

    assert response.status_code == 403


def test_decision_with_a_matching_csrf_cookie_and_header_succeeds():
    sink = InMemoryPendingApprovalsSink()
    sink.put(_red_record())
    app.dependency_overrides.pop(verify_csrf, None)
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: sink
    app.dependency_overrides[get_agent_runtime_client] = lambda: FakeAgentRuntimeClient()
    try:
        test_client = TestClient(app)
        test_client.cookies.set(CSRF_COOKIE_NAME, "matching-value")
        response = test_client.post(
            "/api/approvals/b1:b2/decision", json={"action": "approve"},
            headers={"X-Stacks-CSRF-Token": "matching-value"},
        )
    finally:
        app.dependency_overrides.pop(get_current_claims, None)
        app.dependency_overrides.pop(get_pending_approvals_sink, None)
        app.dependency_overrides.pop(get_agent_runtime_client, None)

    assert response.status_code == 200


# --- 10.1 / 10.2 rate limiting ---

def test_the_approval_endpoint_trips_429_once_its_configured_limit_is_exceeded():
    # The override must return the SAME limiter instance on every call --
    # a lambda that constructs a fresh RateLimiter() per call would give
    # each request its own empty counter and the limit would never trip.
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_approval_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_pending_approvals_sink] = lambda: InMemoryPendingApprovalsSink()
    app.dependency_overrides[get_agent_runtime_client] = lambda: FakeAgentRuntimeClient()
    try:
        test_client = TestClient(app)
        statuses = [
            test_client.post("/api/approvals/no_such_case/decision", json={"action": "approve"}).status_code
            for _ in range(3)
        ]
    finally:
        app.dependency_overrides.pop(get_approval_rate_limiter, None)
        app.dependency_overrides.pop(get_current_claims, None)
        app.dependency_overrides.pop(get_pending_approvals_sink, None)
        app.dependency_overrides.pop(get_agent_runtime_client, None)

    # The first two clear the limiter (whatever the endpoint itself then
    # decides, here 404 since the case doesn't exist); the third never
    # reaches the endpoint body at all.
    assert statuses == [404, 404, 429]


def test_a_read_endpoint_trips_429_once_its_configured_limit_is_exceeded():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_read_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_audit_sink] = lambda: AuditLogSink()
    try:
        test_client = TestClient(app)
        statuses = [test_client.get("/api/audit").status_code for _ in range(3)]
    finally:
        app.dependency_overrides.pop(get_read_rate_limiter, None)
        app.dependency_overrides.pop(get_current_claims, None)
        app.dependency_overrides.pop(get_audit_sink, None)

    assert statuses == [200, 200, 429]


def test_rate_limiter_forgets_hits_once_the_window_has_elapsed():
    limiter = RateLimiter(max_requests=1, window_seconds=0.05)
    limiter.check("key")
    import time
    time.sleep(0.1)
    limiter.check("key")  # does not raise -- the first hit has aged out


def test_rate_limiter_distinguishes_keys():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("session-a")
    limiter.check("session-b")  # a different key has its own independent budget
