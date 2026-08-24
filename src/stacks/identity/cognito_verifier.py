"""Real AgentCore Identity / Cognito claims verifier. RS256, verified
against the pool's own JWKS endpoint via PyJWKClient -- never a shared
secret. See docs/architecture/agent_architecture.md section 4.5.
"""
from __future__ import annotations

import jwt

from stacks.identity.claims import InvalidClaimsError, StaffIdentityClaims


class CognitoClaimsVerifier:
    def __init__(self, user_pool_id: str, region: str, app_client_id: str) -> None:
        self._app_client_id = app_client_id
        issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._issuer = issuer
        self._jwk_client = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")

    def verify(self, token: str) -> StaffIdentityClaims:
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise InvalidClaimsError(str(exc)) from exc
        except jwt.exceptions.PyJWKClientError as exc:
            raise InvalidClaimsError(str(exc)) from exc

        try:
            groups = payload.get("cognito:groups", [])
            role = groups[0] if groups else None
            if role is None:
                raise InvalidClaimsError("token carries no cognito:groups claim")
            return StaffIdentityClaims(
                role=role,
                library_id=payload["custom:library_id"],
                case_review_role=payload.get("custom:case_review_role"),
            )
        except KeyError as exc:
            raise InvalidClaimsError(f"missing required claim: {exc}") from exc
