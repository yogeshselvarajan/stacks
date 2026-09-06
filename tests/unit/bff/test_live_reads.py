"""Exercises the BFF's read endpoints against the real, already-deployed
DynamoDB tables (Plan 3). Safe to run at any time -- read-only, does not
touch the AgentCore Runtime, its EventBridge schedule, or its Lambda.
"""
import os

import pytest
from fastapi.testclient import TestClient


def _client_with_real_repo():
    environment = os.environ.get("STACKS_TEST_DYNAMODB_ENVIRONMENT")
    if not environment:
        pytest.skip("STACKS_TEST_DYNAMODB_ENVIRONMENT not set -- needs Plan 3's real deployed tables")
    from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
    from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink
    from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
    from stacks.identity.claims import StaffIdentityClaims

    from bff.deps import get_audit_sink, get_current_claims, get_pending_approvals_sink, get_repo
    from bff.main import app

    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    app.dependency_overrides[get_current_claims] = lambda: StaffIdentityClaims(
        role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review"
    )
    app.dependency_overrides[get_repo] = lambda: DynamoDBLibraryDataRepository(region=region, environment=environment)
    app.dependency_overrides[get_pending_approvals_sink] = lambda: DynamoDBPendingApprovalsSink(region=region, environment=environment)
    app.dependency_overrides[get_audit_sink] = lambda: DynamoDBAuditLogSink(region=region, environment=environment)
    return TestClient(app)


def test_live_get_calendar_returns_the_real_seeded_demo_bookings():
    client = _client_with_real_repo()
    response = client.get("/api/calendar?room_id=room_a")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_live_get_audit_list_reads_the_real_audit_log_table():
    client = _client_with_real_repo()
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
