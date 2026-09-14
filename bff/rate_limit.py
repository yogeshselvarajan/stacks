# bff/rate_limit.py
"""Per-session/per-IP request rate limiting, per security.md Section 10:
a tighter threshold on the HITL approval endpoint (the single highest-
consequence mutating surface -- every RED-tier action resolves through
it), a lighter one on the read endpoints, and one on login (defense in
depth on top of Cognito's own throttling).

In-memory sliding-window counter, deliberately not Redis/DynamoDB-backed:
this project runs the BFF as a single process (Lambda Function URL / App
Runner, per final_architecture.md's deployment choice), so process-local
state is a correct, zero-extra-infrastructure fit for this scale. A
multi-instance deployment would need a shared store instead -- named here,
not silently assumed away.

Limiter instances are exposed through FastAPI dependency getters (get_*
functions), matching this module's existing deps.py convention, so tests
can override them with a fresh or deliberately tiny instance via
app.dependency_overrides rather than mutating shared global state.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from stacks.identity.claims import StaffIdentityClaims

from bff.deps import get_current_claims


class RateLimiter:
    """Fixed-size sliding-window limiter keyed by an arbitrary string."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            raise HTTPException(status_code=429, detail="rate limit exceeded, slow down")
        hits.append(now)


# A legitimate staff member approves cases at human speed -- a handful per
# session (frontend_architecture.md Section 8's day-in-the-life flows) --
# so this threshold is intentionally far tighter than the read-endpoint one.
_approval_limiter = RateLimiter(max_requests=30, window_seconds=60)

# A queue view polls every 20-30 seconds per frontend_architecture.md
# Section 5.1; several views polling in parallel from one session is still
# a small, predictable volume well under this ceiling.
_read_limiter = RateLimiter(max_requests=120, window_seconds=60)

# Baseline brute-force throttle on top of Cognito's own managed throttling
# (security.md Section 10.2) -- keyed by client IP since there is no
# session yet at login time.
_login_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Case creation triggers a real, billed agent invocation (unlike an
# approval decision, which only resumes one already in flight), so this
# budget is intentionally tighter than _approval_limiter's and kept as its
# own dedicated limiter -- a burst of new-request submissions must not be
# able to lock staff out of approving already-pending cases.
_case_creation_limiter = RateLimiter(max_requests=10, window_seconds=60)


def get_approval_rate_limiter() -> RateLimiter:
    return _approval_limiter


def get_read_rate_limiter() -> RateLimiter:
    return _read_limiter


def get_login_rate_limiter() -> RateLimiter:
    return _login_limiter


def get_case_creation_rate_limiter() -> RateLimiter:
    return _case_creation_limiter


def enforce_approval_rate_limit(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    limiter: RateLimiter = Depends(get_approval_rate_limiter),
) -> None:
    limiter.check(f"{claims.library_id}:{claims.role}")


def enforce_read_rate_limit(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    limiter: RateLimiter = Depends(get_read_rate_limiter),
) -> None:
    limiter.check(f"{claims.library_id}:{claims.role}")


def enforce_login_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_login_rate_limiter),
) -> None:
    key = request.client.host if request.client else "unknown"
    limiter.check(key)


def enforce_case_creation_rate_limit(
    claims: StaffIdentityClaims = Depends(get_current_claims),
    limiter: RateLimiter = Depends(get_case_creation_rate_limiter),
) -> None:
    limiter.check(f"{claims.library_id}:{claims.role}")
