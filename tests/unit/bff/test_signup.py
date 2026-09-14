from unittest.mock import MagicMock, patch

import pytest

from bff.main import app
from bff.rate_limit import RateLimiter, get_signup_rate_limiter


@pytest.fixture(autouse=True)
def _generous_signup_rate_limit():
    # The real _signup_limiter is module-level, process-shared state, so
    # without this override every test in this file posting to
    # /api/auth/signup competes for the same 5-requests/60s budget and
    # later tests spuriously see 429 instead of the status they're
    # actually testing for. The one test that exercises the real limit
    # (below) overrides this again with its own tight, dedicated instance.
    limiter = RateLimiter(max_requests=1000, window_seconds=60)
    app.dependency_overrides[get_signup_rate_limiter] = lambda: limiter
    yield
    app.dependency_overrides.pop(get_signup_rate_limiter, None)


def _fake_cognito_client() -> MagicMock:
    client = MagicMock()
    client.initiate_auth.return_value = {
        "AuthenticationResult": {"IdToken": "fake.id.token", "AccessToken": "fake.access.token", "ExpiresIn": 3600, "TokenType": "Bearer"}
    }
    return client


def test_signup_creates_a_confirmed_user_and_signs_them_in(client):
    fake_client = _fake_cognito_client()
    with patch("bff.auth.boto3.client", return_value=fake_client):
        response = client.post(
            "/api/auth/signup",
            json={"username": "new-demo-user", "password": "Sup3r$ecret!", "role": "circulation_staff"},
        )

    assert response.status_code == 200
    fake_client.admin_create_user.assert_called_once()
    create_kwargs = fake_client.admin_create_user.call_args.kwargs
    assert create_kwargs["Username"] == "new-demo-user"
    assert create_kwargs["MessageAction"] == "SUPPRESS"
    assert {"Name": "custom:library_id", "Value": "lib_demo"} in create_kwargs["UserAttributes"]

    fake_client.admin_set_user_password.assert_called_once()
    assert fake_client.admin_set_user_password.call_args.kwargs["Permanent"] is True

    fake_client.admin_add_user_to_group.assert_called_once()
    assert fake_client.admin_add_user_to_group.call_args.kwargs["GroupName"] == "circulation_staff"

    set_cookie = response.headers["set-cookie"]
    assert "stacks_session=fake.id.token" in set_cookie
    assert "HttpOnly" in set_cookie


def test_signup_sets_case_review_role_only_for_branch_manager(client):
    fake_client = _fake_cognito_client()
    with patch("bff.auth.boto3.client", return_value=fake_client):
        response = client.post(
            "/api/auth/signup",
            json={"username": "new-branch-manager", "password": "Sup3r$ecret!", "role": "branch_manager"},
        )

    assert response.status_code == 200
    create_kwargs = fake_client.admin_create_user.call_args.kwargs
    assert {"Name": "custom:case_review_role", "Value": "librarian_case_review"} in create_kwargs["UserAttributes"]


def test_signup_rejects_a_role_outside_the_known_demo_roles(client):
    response = client.post(
        "/api/auth/signup",
        json={"username": "new-demo-user", "password": "Sup3r$ecret!", "role": "super_admin"},
    )
    assert response.status_code == 422


def test_signup_rejects_an_unsafe_username(client):
    response = client.post(
        "/api/auth/signup",
        json={"username": "not a valid username!", "password": "Sup3r$ecret!", "role": "circulation_staff"},
    )
    assert response.status_code == 422


def test_signup_with_a_taken_username_returns_409_and_sets_no_cookie(client):
    from botocore.exceptions import ClientError

    fake_client = _fake_cognito_client()
    fake_client.admin_create_user.side_effect = ClientError(
        {"Error": {"Code": "UsernameExistsException", "Message": "already exists"}}, "AdminCreateUser"
    )
    with patch("bff.auth.boto3.client", return_value=fake_client):
        response = client.post(
            "/api/auth/signup",
            json={"username": "test-branch-manager", "password": "Sup3r$ecret!", "role": "branch_manager"},
        )

    assert response.status_code == 409
    assert "set-cookie" not in response.headers


def test_signup_with_a_weak_password_returns_400(client):
    from botocore.exceptions import ClientError

    fake_client = _fake_cognito_client()
    fake_client.admin_create_user.side_effect = ClientError(
        {"Error": {"Code": "InvalidPasswordException", "Message": "too weak"}}, "AdminCreateUser"
    )
    with patch("bff.auth.boto3.client", return_value=fake_client):
        response = client.post(
            "/api/auth/signup",
            json={"username": "new-demo-user", "password": "weak", "role": "circulation_staff"},
        )

    assert response.status_code == 400


def test_signup_cleans_up_the_orphaned_user_if_password_or_group_assignment_fails(client):
    from botocore.exceptions import ClientError

    fake_client = _fake_cognito_client()
    fake_client.admin_set_user_password.side_effect = ClientError(
        {"Error": {"Code": "InternalErrorException", "Message": "transient"}}, "AdminSetUserPassword"
    )
    with patch("bff.auth.boto3.client", return_value=fake_client):
        response = client.post(
            "/api/auth/signup",
            json={"username": "new-demo-user", "password": "Sup3r$ecret!", "role": "circulation_staff"},
        )

    assert response.status_code == 400
    fake_client.admin_delete_user.assert_called_once()
    assert fake_client.admin_delete_user.call_args.kwargs["Username"] == "new-demo-user"


def test_the_signup_endpoint_trips_429_once_its_configured_limit_is_exceeded(client):
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_signup_rate_limiter] = lambda: limiter
    fake_client = _fake_cognito_client()
    try:
        with patch("bff.auth.boto3.client", return_value=fake_client):
            statuses = [
                client.post(
                    "/api/auth/signup",
                    json={"username": f"demo-user-{i}", "password": "Sup3r$ecret!", "role": "circulation_staff"},
                ).status_code
                for i in range(3)
            ]
    finally:
        app.dependency_overrides.pop(get_signup_rate_limiter, None)

    assert statuses[:2] == [200, 200]
    assert statuses[2] == 429
