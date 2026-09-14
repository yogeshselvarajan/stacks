# bff/auth.py
"""POST /api/auth/login: calls Cognito's real InitiateAuth (USER_PASSWORD_AUTH
flow, confirmed against the live boto3 service model this session) and sets
the returned ID token in an HttpOnly, Secure, SameSite=Strict cookie. The ID
token carries the cognito:groups and custom:library_id/custom:case_review_role
claims (the access token does not), per CognitoClaimsVerifier.verify's own
claim reads.
"""
from __future__ import annotations

import re

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, field_validator

from stacks.identity.claims import StaffIdentityClaims

from bff.config import COGNITO_APP_CLIENT_ID, COGNITO_USER_POOL_ID, REGION, SESSION_COOKIE_NAME
from bff.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from bff.deps import get_current_claims
from bff.rate_limit import enforce_login_rate_limit, enforce_signup_rate_limit
from fastapi import Depends

router = APIRouter()

# Self-service sign-up is scoped to this project's own single demo tenant
# and to exactly the four roles the rest of the product already knows
# about (bff/workflow_authz.py's WORKFLOW_OWNING_ROLE, plus branch_manager)
# -- never a client-supplied library_id or an arbitrary group name. A
# self-signed-up branch_manager can see every workflow and act on
# approvals, same as the pre-provisioned test-branch-manager account; that
# is an intentional demo-persona choice (see the AWS docs grounding this
# endpoint's approach: AdminCreateUser + AdminSetUserPassword(Permanent)
# lands a user in CONFIRMED status immediately, no email verification and
# no Lambda trigger required), not a privilege-escalation gap, since every
# self-signed-up user still only ever reaches lib_demo's own synthetic data.
SIGNUP_ROLE_TO_GROUP = {
    "branch_manager": "branch_manager",
    "circulation_staff": "circulation_staff",
    "room_booking_staff": "room_booking_staff",
    "ill_coordinator": "ill_coordinator",
}
SIGNUP_LIBRARY_ID = "lib_demo"
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str
    role: str

    @field_validator("username")
    @classmethod
    def _username_is_a_safe_cognito_identifier(cls, value: str) -> str:
        if not (3 <= len(value) <= 64) or not _USERNAME_PATTERN.match(value):
            raise ValueError("username must be 3-64 characters, letters/numbers/hyphens/underscores only")
        return value

    @field_validator("role")
    @classmethod
    def _role_is_a_known_demo_role(cls, value: str) -> str:
        if value not in SIGNUP_ROLE_TO_GROUP:
            raise ValueError(f"role must be one of {sorted(SIGNUP_ROLE_TO_GROUP)}")
        return value


class SessionResponse(BaseModel):
    role: str
    libraryId: str
    caseReviewRole: str | None


@router.post("/api/auth/login", dependencies=[Depends(enforce_login_rate_limit)])
def login(body: LoginRequest, response: Response) -> dict:
    client = boto3.client("cognito-idp", region_name=REGION)
    try:
        result = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body.username, "PASSWORD": body.password},
            ClientId=COGNITO_APP_CLIENT_ID,
        )
    except ClientError as exc:
        raise HTTPException(status_code=401, detail="Incorrect username or password.") from exc

    id_token = result["AuthenticationResult"]["IdToken"]
    expires_in = result["AuthenticationResult"]["ExpiresIn"]
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=id_token, httponly=True, secure=True,
        samesite="Strict", max_age=expires_in,
    )
    # Not HttpOnly: the frontend must be able to read this value in order
    # to echo it back as the X-Stacks-CSRF-Token header (bff/csrf.py).
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=generate_csrf_token(), httponly=False, secure=True,
        samesite="Strict", max_age=expires_in,
    )
    return {"status": "ok"}


@router.post("/api/auth/signup", dependencies=[Depends(enforce_signup_rate_limit)])
def signup(body: SignupRequest, response: Response) -> dict:
    client = boto3.client("cognito-idp", region_name=REGION)
    group = SIGNUP_ROLE_TO_GROUP[body.role]
    attrs = [{"Name": "custom:library_id", "Value": SIGNUP_LIBRARY_ID}]
    if body.role == "branch_manager":
        attrs.append({"Name": "custom:case_review_role", "Value": "librarian_case_review"})

    try:
        client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID, Username=body.username,
            UserAttributes=attrs, MessageAction="SUPPRESS", TemporaryPassword=body.password,
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "UsernameExistsException":
            raise HTTPException(status_code=409, detail="That username is already taken.") from exc
        if error_code == "InvalidPasswordException":
            raise HTTPException(status_code=400, detail="Password does not meet the minimum requirements.") from exc
        raise HTTPException(status_code=400, detail="Could not create that account.") from exc

    # AdminCreateUser alone leaves the user in FORCE_CHANGE_PASSWORD, not
    # signed-in-ready -- AdminSetUserPassword(Permanent=True) is what moves
    # them straight to CONFIRMED (confirmed against the live AWS API
    # reference: "After the user sets a new password, or if you set a
    # permanent password, their status becomes Confirmed"), the same two-
    # call sequence scripts/provision_cognito.py already uses for every
    # pre-provisioned test user.
    try:
        client.admin_set_user_password(UserPoolId=COGNITO_USER_POOL_ID, Username=body.username, Password=body.password, Permanent=True)
        client.admin_add_user_to_group(UserPoolId=COGNITO_USER_POOL_ID, Username=body.username, GroupName=group)
    except ClientError as exc:
        client.admin_delete_user(UserPoolId=COGNITO_USER_POOL_ID, Username=body.username)
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "InvalidPasswordException":
            raise HTTPException(status_code=400, detail="Password does not meet the minimum requirements.") from exc
        raise HTTPException(status_code=400, detail="Could not create that account.") from exc

    result = client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": body.username, "PASSWORD": body.password},
        ClientId=COGNITO_APP_CLIENT_ID,
    )
    id_token = result["AuthenticationResult"]["IdToken"]
    expires_in = result["AuthenticationResult"]["ExpiresIn"]
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=id_token, httponly=True, secure=True,
        samesite="Strict", max_age=expires_in,
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=generate_csrf_token(), httponly=False, secure=True,
        samesite="Strict", max_age=expires_in,
    )
    return {"status": "ok"}


@router.post("/api/auth/logout")
def logout(response: Response) -> dict:
    # No claims dependency here on purpose: logging out an already-expired
    # or already-cleared session must still succeed (idempotent), not 401
    # on its own way out. delete_cookie must be called with the exact same
    # path/domain the cookie was set with, or the browser treats it as a
    # different cookie and leaves the original in place.
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    response.delete_cookie(key=CSRF_COOKIE_NAME)
    return {"status": "ok"}


@router.get("/api/session", response_model=SessionResponse)
def get_session(claims: StaffIdentityClaims = Depends(get_current_claims)) -> SessionResponse:
    return SessionResponse(role=claims.role, libraryId=claims.library_id, caseReviewRole=claims.case_review_role)
