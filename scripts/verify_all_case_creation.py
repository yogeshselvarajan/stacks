"""Manual, one-time verification that all three real case-creation
endpoints (POST /api/ill-requests, POST /api/overdue-cases, POST
/api/bookings) work against a running BFF and the real deployed
AgentCore Runtime. Run with the BFF already running locally
(STACKS_COGNITO_USER_POOL_ID and STACKS_COGNITO_APP_CLIENT_ID set, see
CLAUDE.md's login instructions) and a valid demo user's credentials:

    python scripts/verify_all_case_creation.py <username> <password>

The room-booking case deliberately submits a new room_a booking for
2026-09-01T10:15:00+00:00 to 2026-09-01T10:45:00+00:00, which overlaps
the seeded demo booking b_recurring_a (2026-09-01T10:00:00+00:00 to
2026-09-01T11:00:00+00:00, per src/stacks/data/fixtures.py), so this
exercises the real conflict path, not no_conflict.

Never imported by test code. Creates real records in the live demo
tenant -- clean them up afterward (see the task brief this script was
written for).
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
    headers = {"X-Stacks-CSRF-Token": csrf_token}

    ill_response = session.post(
        f"{BFF_BASE_URL}/api/ill-requests",
        json={"requestedTitle": "Manual Verification Book (all-workflows)", "requesterPatronId": "patron_manual_verify_all"},
        headers=headers,
        cookies=cookies,
    )
    ill_response.raise_for_status()
    print("ILL request created:", ill_response.json())

    overdue_response = session.post(
        f"{BFF_BASE_URL}/api/overdue-cases",
        json={
            "patronId": "patron_manual_verify_all",
            "itemId": "item_manual_verify_all",
            "itemType": "book",
            "daysOverdue": 5,
            "sensitivityFlag": False,
        },
        headers=headers,
        cookies=cookies,
    )
    overdue_response.raise_for_status()
    print("Overdue case created:", overdue_response.json())

    booking_response = session.post(
        f"{BFF_BASE_URL}/api/bookings",
        json={
            "roomId": "room_a",
            "start": "2026-09-01T10:15:00+00:00",
            "end": "2026-09-01T10:45:00+00:00",
            "bookingType": "staff_internal",
            "bookedBy": "patron_manual_verify_all",
        },
        headers=headers,
        cookies=cookies,
    )
    booking_response.raise_for_status()
    print("Booking created:", booking_response.json())


if __name__ == "__main__":
    main()
