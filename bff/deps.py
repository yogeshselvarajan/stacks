# bff/deps.py
"""FastAPI dependencies: cookie extraction and JWT verification. The
verifier itself is swappable (a plain function returning a
CognitoClaimsVerifier instance), so tests override get_current_claims
directly via FastAPI's dependency_overrides rather than mocking JWKS
network calls.
"""
from __future__ import annotations

from fastapi import Cookie, HTTPException

from stacks.identity.claims import InvalidClaimsError, StaffIdentityClaims
from stacks.identity.cognito_verifier import CognitoClaimsVerifier

from bff.config import COGNITO_APP_CLIENT_ID, COGNITO_USER_POOL_ID, REGION, SESSION_COOKIE_NAME

_verifier: CognitoClaimsVerifier | None = None


def _get_verifier() -> CognitoClaimsVerifier:
    global _verifier
    if _verifier is None:
        _verifier = CognitoClaimsVerifier(user_pool_id=COGNITO_USER_POOL_ID, region=REGION, app_client_id=COGNITO_APP_CLIENT_ID)
    return _verifier


def get_current_claims(stacks_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> StaffIdentityClaims:
    if stacks_session is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        return _get_verifier().verify(stacks_session)
    except InvalidClaimsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
