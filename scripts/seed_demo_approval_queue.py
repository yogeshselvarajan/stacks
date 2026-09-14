"""Populates the Approval Inbox with one real, live-agent-produced pending
case per workflow (ILL routing, room booking, overdue chasing), so a judge
who signs in sees a genuinely populated queue instead of an empty one.

Every pending case here is a REAL artifact of the deployed system doing its
own job: this script calls the live BFF over HTTPS (the same
judge-login -> CSRF -> AgentCore Runtime path any staff user goes through),
not a direct database write of a fake "pending" row. The one exception is a
single flagged room booking (b_seed_minor_flagged), seeded directly via the
repository before the live call -- BookingRecord.flags is not settable
through the public create-booking API (by design: only a librarian curating
fixture data sets a sensitivity flag directly, never an ordinary booking
request), so a MINOR_ACCOUNT-flagged booking has to exist first for the live
conflict-resolution call to react to, exactly mirroring how
stacks.data.fixtures.seed_demo_library seeds its own RED room-booking case
(b_recurring_b) the same way.

Idempotent to run more than once: re-running creates a fresh set of cases
(the previous run's cases, if still pending, are simply joined by new ones),
so run scripts/seed_dynamodb.py first if you want a clean baseline, then
this script once before a demo or judging session:

    python scripts/seed_dynamodb.py
    python scripts/seed_demo_approval_queue.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import httpx

from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.data.models import BookingRecord, BookingType
from stacks.types import SensitivityFlag

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
LIBRARY_ID = "lib_demo"

BFF_BASE_URL = os.environ.get("STACKS_BFF_BASE_URL")
FRONTEND_ORIGIN = os.environ.get("STACKS_FRONTEND_ORIGIN", "https://main.d1f4dnxaaugevn.amplifyapp.com")

# A previously-unused room_b time slot (the existing fixture's room_b
# bookings both sit on 2026-09-03; this is a different day entirely, so it
# cannot collide with them or with anything create_booking itself creates
# in a normal demo session) -- keeps the RED case a clean two-way conflict
# instead of a confusing three-way one.
_SEED_SLOT_START = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)
_SEED_SLOT_END = datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc)
_CONFLICTING_SLOT_START = "2026-09-10T16:15:00+00:00"
_CONFLICTING_SLOT_END = "2026-09-10T16:45:00+00:00"


def _seed_flagged_room_booking() -> None:
    repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    repo.save_booking(BookingRecord(
        booking_id="b_seed_minor_flagged", library_id=LIBRARY_ID, room_id="room_b",
        start=_SEED_SLOT_START, end=_SEED_SLOT_END,
        booked_by="patron_teen_group", booking_type=BookingType.RECURRING_PROGRAM,
        flags=[SensitivityFlag.MINOR_ACCOUNT], notes="Teen manga club",
    ))
    print("Seeded a flagged room_b booking (b_seed_minor_flagged) for the RED conflict scenario.")


def _judge_login(client: httpx.Client) -> str:
    response = client.post(f"{BFF_BASE_URL}/api/auth/judge-login", headers={"Origin": FRONTEND_ORIGIN})
    response.raise_for_status()
    return response.json()["csrfToken"]


def _create_ambiguous_ill_case(client: httpx.Client, csrf_token: str) -> None:
    response = client.post(
        f"{BFF_BASE_URL}/api/ill-requests",
        headers={"Origin": FRONTEND_ORIGIN, "X-Stacks-CSRF-Token": csrf_token},
        json={"requestedTitle": "Middlemarch", "requesterPatronId": "patron_ill_2"},
    )
    response.raise_for_status()
    body = response.json()
    print(f"ILL routing case {body['illRequestId']}: status={body['status']} (expect pending_approval, YELLOW)")


def _create_flagged_room_conflict(client: httpx.Client, csrf_token: str) -> None:
    response = client.post(
        f"{BFF_BASE_URL}/api/bookings",
        headers={"Origin": FRONTEND_ORIGIN, "X-Stacks-CSRF-Token": csrf_token},
        json={
            "roomId": "room_b", "start": _CONFLICTING_SLOT_START, "end": _CONFLICTING_SLOT_END,
            "bookingType": "walk_in", "bookedBy": "patron_walkin_seed",
        },
    )
    response.raise_for_status()
    body = response.json()
    print(f"Room booking case {body['bookingId']}: status={body['status']} (expect pending_approval, RED)")


def _create_sensitive_overdue_case(client: httpx.Client, csrf_token: str) -> None:
    response = client.post(
        f"{BFF_BASE_URL}/api/overdue-cases",
        headers={"Origin": FRONTEND_ORIGIN, "X-Stacks-CSRF-Token": csrf_token},
        json={
            "patronId": "patron_overdue_4", "itemId": "item_seed_overdue",
            "itemType": "book", "daysOverdue": 45, "sensitivityFlag": True,
        },
    )
    response.raise_for_status()
    body = response.json()
    print(f"Overdue case {body['circulationRecordId']}: status={body['status']} (expect pending_approval, RED)")


def main() -> None:
    if not BFF_BASE_URL:
        print("STACKS_BFF_BASE_URL must be set to the live BFF's base URL.", file=sys.stderr)
        raise SystemExit(1)

    _seed_flagged_room_booking()

    with httpx.Client(timeout=30.0) as client:
        csrf_token = _judge_login(client)
        _create_ambiguous_ill_case(client, csrf_token)
        _create_flagged_room_conflict(client, csrf_token)
        _create_sensitive_overdue_case(client, csrf_token)

    print("Done. All three cases are left pending for a judge to review and approve themselves.")


if __name__ == "__main__":
    main()
