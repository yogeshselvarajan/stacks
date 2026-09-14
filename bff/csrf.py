# bff/csrf.py
"""Double-submit-cookie CSRF protection, per security.md Section 8.2:
SameSite=Strict on the session cookie is the first layer; this is the
second, independent one. login() issues a per-session token in a
non-HttpOnly cookie (the frontend must be able to read it to echo it
back) -- a cross-site form submission can attach the cookie automatically
but cannot read its value to also set the header, so it cannot produce a
match.

No server-side token store: the value only ever needs to be compared
against itself (cookie vs. header), never looked up, so there is nothing
for a database to add here.

This entire mechanism assumes the browser stores and sends the CSRF
cookie at all. Chrome and Edge Incognito/InPrivate windows block
third-party cookies by default -- a stricter, separate mechanism from
SameSite -- so on the cross-origin deployment (frontend on Amplify, BFF
on a separate Lambda Function URL) this cookie never reaches the browser
in a private window in the first place, and this check would otherwise
403 every write request there even for a genuine, authenticated caller.
The Authorization Bearer path (bff/deps.py's get_current_claims) is
immune to CSRF by construction, independent of this cookie: forging a
request with a custom Authorization header requires either reading the
legitimate in-memory token (impossible for a hostile origin, blocked by
CORS) or the browser auto-attaching it (cookies auto-attach; a header
set by JS never does). So a request already authenticated that way skips
this check rather than failing a mechanism it doesn't need.
"""
from __future__ import annotations

import secrets

from fastapi import Cookie, Header, HTTPException

CSRF_COOKIE_NAME = "stacks_csrf"
CSRF_HEADER_NAME = "X-Stacks-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(
    stacks_csrf: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    x_stacks_csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    authorization: str | None = Header(default=None),
) -> None:
    if authorization and authorization.startswith("Bearer "):
        return
    if not stacks_csrf or not x_stacks_csrf_token or not secrets.compare_digest(stacks_csrf, x_stacks_csrf_token):
        raise HTTPException(status_code=403, detail="missing or invalid CSRF token")
