# tests/unit/bff/conftest.py
"""Shared BFF test fixtures. The claims-verifier dependency is overridden
per-test via FastAPI's own dependency_overrides mechanism (fake verifier
for fast tests, matching this project's existing FakeClaimsVerifier
convention from src/stacks/identity/claims.py), never a real Cognito
call in the fast suite.

Rate limiting and CSRF verification are neutralized here by default, the
same way -- every pre-existing test in this suite calls mutating/read
endpoints without simulating a real browser's cookie/header dance, and
without this autouse fixture the new controls in bff/rate_limit.py and
bff/csrf.py would 403/429 every one of them. test_security_controls.py
re-enables the real behavior per test by overriding these dependencies
again (or popping the override) within its own test bodies.
"""
import pytest
from fastapi.testclient import TestClient

from bff.csrf import verify_csrf
from bff.main import app
from bff.rate_limit import RateLimiter, get_approval_rate_limiter, get_login_rate_limiter, get_read_rate_limiter


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _permissive_security_controls():
    app.dependency_overrides[verify_csrf] = lambda: None
    app.dependency_overrides[get_approval_rate_limiter] = lambda: RateLimiter(max_requests=10_000, window_seconds=60)
    app.dependency_overrides[get_read_rate_limiter] = lambda: RateLimiter(max_requests=10_000, window_seconds=60)
    app.dependency_overrides[get_login_rate_limiter] = lambda: RateLimiter(max_requests=10_000, window_seconds=60)
    yield
    app.dependency_overrides.pop(verify_csrf, None)
    app.dependency_overrides.pop(get_approval_rate_limiter, None)
    app.dependency_overrides.pop(get_read_rate_limiter, None)
    app.dependency_overrides.pop(get_login_rate_limiter, None)
