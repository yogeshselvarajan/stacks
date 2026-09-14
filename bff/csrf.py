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
) -> None:
    if not stacks_csrf or not x_stacks_csrf_token or not secrets.compare_digest(stacks_csrf, x_stacks_csrf_token):
        raise HTTPException(status_code=403, detail="missing or invalid CSRF token")
