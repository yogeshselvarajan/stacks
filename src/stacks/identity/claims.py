"""Identity claims shared by every ClaimsVerifier implementation.

StaffIdentityClaims is the one shape a verified staff identity is reduced
to before it reaches any tool or hook -- mirrors
docs/architecture/agent_architecture.md section 4.5's exact claim table
(role, library_id, and the case_review_role that must equal exactly
"librarian_case_review" to satisfy a RED approval, per
stacks.hitl.classify.RED_APPROVER_ROLE).
"""
from __future__ import annotations

import secrets
import time
import uuid
from typing import Protocol

import jwt
from pydantic import BaseModel


class StaffIdentityClaims(BaseModel):
    role: str
    library_id: str
    case_review_role: str | None = None


class InvalidClaimsError(Exception):
    """Raised by any ClaimsVerifier implementation on an invalid, expired,
    or malformed token. Callers never inspect a raw JWT themselves -- this
    is the one boundary where verification happens (final_architecture.md
    section 10.4, step 2)."""


class ClaimsVerifier(Protocol):
    def verify(self, token: str) -> StaffIdentityClaims: ...


class FakeClaimsVerifier:
    """HS256, single-instance test secret. Never used against a real
    Cognito pool -- CognitoClaimsVerifier (Task 3) is the real
    implementation, RS256, verified against Cognito's own JWKS endpoint.
    """

    def __init__(self) -> None:
        self._secret = secrets.token_hex(32)

    def mint(
        self,
        role: str,
        library_id: str,
        case_review_role: str | None = None,
        expired: bool = False,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": str(uuid.uuid4()),
            "role": role,
            "library_id": library_id,
            "iat": now,
            "exp": now - 3600 if expired else now + 3600,
        }
        if case_review_role is not None:
            payload["custom:case_review_role"] = case_review_role
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str) -> StaffIdentityClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise InvalidClaimsError(str(exc)) from exc
        try:
            return StaffIdentityClaims(
                role=payload["role"],
                library_id=payload["library_id"],
                case_review_role=payload.get("custom:case_review_role"),
            )
        except KeyError as exc:
            raise InvalidClaimsError(f"missing required claim: {exc}") from exc
