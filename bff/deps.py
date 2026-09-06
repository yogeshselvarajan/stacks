# bff/deps.py
"""FastAPI dependencies: cookie extraction and JWT verification. The
verifier itself is swappable (a plain function returning a
CognitoClaimsVerifier instance), so tests override get_current_claims
directly via FastAPI's dependency_overrides rather than mocking JWKS
network calls.
"""
from __future__ import annotations

from fastapi import Cookie, HTTPException

from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.data.repository import LibraryDataRepository
from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink
from stacks.hitl.pending_approvals import PendingApprovalsSink
from stacks.hooks.audit_log import AuditLogSink
from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
from stacks.identity.claims import InvalidClaimsError, StaffIdentityClaims
from stacks.identity.cognito_verifier import CognitoClaimsVerifier

from bff.config import COGNITO_APP_CLIENT_ID, COGNITO_USER_POOL_ID, ENVIRONMENT, REGION, SESSION_COOKIE_NAME

_verifier: CognitoClaimsVerifier | None = None
_repo: LibraryDataRepository | None = None
_pending_approvals_sink: PendingApprovalsSink | None = None
_audit_sink: AuditLogSink | None = None


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


def get_repo() -> LibraryDataRepository:
    global _repo
    if _repo is None:
        _repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    return _repo


def get_pending_approvals_sink() -> PendingApprovalsSink:
    global _pending_approvals_sink
    if _pending_approvals_sink is None:
        _pending_approvals_sink = DynamoDBPendingApprovalsSink(region=REGION, environment=ENVIRONMENT)
    return _pending_approvals_sink


def get_audit_sink() -> AuditLogSink:
    global _audit_sink
    if _audit_sink is None:
        _audit_sink = DynamoDBAuditLogSink(region=REGION, environment=ENVIRONMENT)
    return _audit_sink
