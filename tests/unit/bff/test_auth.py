from unittest.mock import MagicMock, patch


def test_login_sets_an_httponly_secure_samesite_cookie_on_success(client):
    fake_cognito_response = {
        "AuthenticationResult": {"IdToken": "fake.id.token", "AccessToken": "fake.access.token", "ExpiresIn": 3600, "TokenType": "Bearer"}
    }
    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.return_value = fake_cognito_response
        response = client.post("/api/auth/login", json={"username": "test-branch-manager", "password": "hunter2"})

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert "stacks_session=fake.id.token" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=Strict" in set_cookie


def test_login_with_wrong_credentials_returns_401_and_sets_no_cookie(client):
    from botocore.exceptions import ClientError

    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect username or password."}}, "InitiateAuth"
        )
        response = client.post("/api/auth/login", json={"username": "test-branch-manager", "password": "wrong"})

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_session_endpoint_returns_the_verified_claims(client):
    from stacks.identity.claims import StaffIdentityClaims

    fake_claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")

    def _fake_get_current_claims():
        return fake_claims

    from bff.deps import get_current_claims
    from bff.main import app
    app.dependency_overrides[get_current_claims] = _fake_get_current_claims
    try:
        response = client.get("/api/session")
    finally:
        app.dependency_overrides.pop(get_current_claims, None)

    assert response.status_code == 200
    body = response.json()
    assert body == {"role": "branch_manager", "libraryId": "lib_demo", "caseReviewRole": "librarian_case_review"}


def test_session_endpoint_without_a_cookie_returns_401(client):
    response = client.get("/api/session")
    assert response.status_code == 401


def test_logout_clears_the_session_and_csrf_cookies(client):
    fake_cognito_response = {
        "AuthenticationResult": {"IdToken": "fake.id.token", "AccessToken": "fake.access.token", "ExpiresIn": 3600, "TokenType": "Bearer"}
    }
    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.return_value = fake_cognito_response
        client.post("/api/auth/login", json={"username": "test-branch-manager", "password": "hunter2"})

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    set_cookie_headers = response.headers.get_list("set-cookie")
    session_cookie = next(h for h in set_cookie_headers if h.startswith("stacks_session="))
    csrf_cookie = next(h for h in set_cookie_headers if h.startswith("stacks_csrf="))
    assert 'stacks_session=""' in session_cookie or "stacks_session=" in session_cookie.split(";")[0]
    assert "Max-Age=0" in session_cookie or "expires=" in session_cookie.lower()
    assert "Max-Age=0" in csrf_cookie or "expires=" in csrf_cookie.lower()


def test_logout_without_an_existing_session_still_returns_200(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200


def test_judge_login_signs_in_using_server_side_credentials_only(client, monkeypatch):
    # No credential appears anywhere in the request the client sends --
    # this is the whole point of the route. The username/password used
    # to authenticate come only from the server's own config, never from
    # body.
    monkeypatch.setattr("bff.auth.JUDGE_USERNAME", "test-branch-manager")
    monkeypatch.setattr("bff.auth.JUDGE_PASSWORD", "real-server-side-only-password")
    fake_cognito_response = {
        "AuthenticationResult": {"IdToken": "judge.id.token", "AccessToken": "judge.access.token", "ExpiresIn": 3600, "TokenType": "Bearer"}
    }
    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.return_value = fake_cognito_response
        response = client.post("/api/auth/judge-login")
        call_kwargs = mock_boto_client.return_value.initiate_auth.call_args.kwargs

    assert response.status_code == 200
    assert call_kwargs["AuthParameters"] == {"USERNAME": "test-branch-manager", "PASSWORD": "real-server-side-only-password"}
    set_cookie = response.headers["set-cookie"]
    assert "stacks_session=judge.id.token" in set_cookie
    assert "HttpOnly" in set_cookie


def test_judge_login_returns_503_when_not_configured(client, monkeypatch):
    monkeypatch.setattr("bff.auth.JUDGE_PASSWORD", "")
    response = client.post("/api/auth/judge-login")
    assert response.status_code == 503


def test_judge_login_returns_503_not_401_if_cognito_call_itself_fails(client, monkeypatch):
    # A misconfigured judge account (wrong password set server-side, or
    # the account disabled) is an operational problem, not something to
    # blame on "incorrect credentials" the way a normal failed login
    # would -- the judge never entered anything.
    from botocore.exceptions import ClientError

    monkeypatch.setattr("bff.auth.JUDGE_USERNAME", "test-branch-manager")
    monkeypatch.setattr("bff.auth.JUDGE_PASSWORD", "stale-password")
    with patch("bff.auth.boto3.client") as mock_boto_client:
        mock_boto_client.return_value.initiate_auth.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect username or password."}}, "InitiateAuth"
        )
        response = client.post("/api/auth/judge-login")

    assert response.status_code == 503
    assert "set-cookie" not in response.headers
