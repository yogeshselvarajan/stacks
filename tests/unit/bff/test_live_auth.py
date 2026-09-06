"""Exercises the real Cognito user pool created by scripts/provision_cognito.py
(Plan 2). Safe to run at any time -- this is authentication only, does not
touch the AgentCore Runtime, its EventBridge schedule, or its Lambda.
"""
import os

import pytest
from fastapi.testclient import TestClient


def _client():
    if not os.environ.get("STACKS_TEST_COGNITO_POOL_ID"):
        pytest.skip("STACKS_TEST_COGNITO_POOL_ID not set -- run scripts/provision_cognito.py first (Plan 2)")
    from bff.main import app
    return TestClient(app)


def test_live_login_with_the_real_provisioned_test_user_succeeds():
    client = _client()
    username = os.environ.get("STACKS_TEST_COGNITO_USERNAME", "test-branch-manager")
    password = os.environ["STACKS_TEST_COGNITO_PASSWORD"]
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    assert "stacks_session=" in response.headers["set-cookie"]


def test_live_session_after_a_real_login_returns_the_real_claims():
    client = _client()
    username = os.environ.get("STACKS_TEST_COGNITO_USERNAME", "test-branch-manager")
    password = os.environ["STACKS_TEST_COGNITO_PASSWORD"]
    login_response = client.post("/api/auth/login", json={"username": username, "password": password})
    cookie = login_response.headers["set-cookie"].split(";")[0]
    session_response = client.get("/api/session", headers={"cookie": cookie})
    assert session_response.status_code == 200
    assert session_response.json()["role"] == "branch_manager"
