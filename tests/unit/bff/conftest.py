# tests/unit/bff/conftest.py
"""Shared BFF test fixtures. The claims-verifier dependency is overridden
per-test via FastAPI's own dependency_overrides mechanism (fake verifier
for fast tests, matching this project's existing FakeClaimsVerifier
convention from src/stacks/identity/claims.py), never a real Cognito
call in the fast suite.
"""
import pytest
from fastapi.testclient import TestClient

from bff.main import app


@pytest.fixture
def client():
    return TestClient(app)
