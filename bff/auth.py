# bff/auth.py
"""POST /api/auth/login: calls Cognito's real InitiateAuth (USER_PASSWORD_AUTH
flow, confirmed against the live boto3 service model this session) and sets
the returned ID token in an HttpOnly, Secure, SameSite=Strict cookie. The ID
token carries the cognito:groups and custom:library_id/custom:case_review_role
claims (the access token does not), per CognitoClaimsVerifier.verify's own
claim reads.
"""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from stacks.identity.claims import StaffIdentityClaims

from bff.config import COGNITO_APP_CLIENT_ID, REGION, SESSION_COOKIE_NAME
from bff.deps import get_current_claims
from fastapi import Depends

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    role: str
    libraryId: str
    caseReviewRole: str | None


@router.post("/api/auth/login")
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
    return {"status": "ok"}


@router.get("/api/session", response_model=SessionResponse)
def get_session(claims: StaffIdentityClaims = Depends(get_current_claims)) -> SessionResponse:
    return SessionResponse(role=claims.role, libraryId=claims.library_id, caseReviewRole=claims.case_review_role)
