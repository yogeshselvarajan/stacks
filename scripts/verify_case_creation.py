"""Manual, one-time verification that POST /api/ill-requests works against
a running BFF and the real deployed AgentCore Runtime. Run with the BFF
already running locally (STACKS_COGNITO_USER_POOL_ID and
STACKS_COGNITO_APP_CLIENT_ID set, see CLAUDE.md's login instructions) and
a valid demo user's credentials:

    python scripts/verify_case_creation.py <username> <password>

Never imported by test code.
"""
from __future__ import annotations

import sys

import requests

BFF_BASE_URL = "http://localhost:8000"


def main() -> None:
    username, password = sys.argv[1], sys.argv[2]
    session = requests.Session()

    login = session.post(f"{BFF_BASE_URL}/api/auth/login", json={"username": username, "password": password})
    login.raise_for_status()
    csrf_token = session.cookies.get("stacks_csrf")

    # Explicitly include all session cookies in the request to work around
    # requests.Session's cookie domain matching behavior
    cookies = dict(session.cookies)
    cookies["stacks_csrf"] = csrf_token

    response = session.post(
        f"{BFF_BASE_URL}/api/ill-requests",
        json={"requestedTitle": "Manual Verification Book", "requesterPatronId": "patron_manual_verify"},
        headers={"X-Stacks-CSRF-Token": csrf_token},
        cookies=cookies,
    )
    response.raise_for_status()
    print("Created:", response.json())

    queue = session.get(f"{BFF_BASE_URL}/api/ill-queue", cookies=cookies)
    queue.raise_for_status()
    created_id = response.json()["illRequestId"]
    assert any(r["illRequestId"] == created_id for r in queue.json()), "created request missing from ILL queue"
    print("Confirmed present in /api/ill-queue.")


if __name__ == "__main__":
    main()
