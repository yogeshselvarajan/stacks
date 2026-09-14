"""Populates a realistic, full-spectrum demo dataset across all three
workflows (room booking, ILL routing, overdue chasing), so a judge who
signs in sees a genuinely populated product -- every queue comfortably
above ten rows, and every GREEN/YELLOW/RED tier represented at least once
per workflow, not just a handful of pending cases.

Every case here is a REAL artifact of the deployed system doing its own
job: this script calls the live BFF over HTTPS (the same
judge-login -> CSRF -> AgentCore Runtime path any staff user goes through),
not a direct database write of a fake "resolved" or "pending" row. The one
exception is a single flagged room booking (b_seed_minor_flagged), seeded
directly via the repository before the live call -- BookingRecord.flags is
not settable through the public create-booking API (by design: only a
librarian curating fixture data sets a sensitivity flag directly, never an
ordinary booking request), so a MINOR_ACCOUNT-flagged booking has to exist
first for the live conflict-resolution call to react to, exactly mirroring
how stacks.data.fixtures.seed_demo_library seeds its own RED room-booking
case (b_recurring_b) the same way.

Covers, per workflow:
  - room booking: 1 RED conflict (a minor's account involved, pending
    human approval), 1 GREEN conflict (two unflagged bookings, resolved
    automatically), 3 standalone no-conflict bookings
  - ILL routing: 1 YELLOW ambiguous case (pending approval), 3 GREEN
    unambiguous cases (auto-routed, reusing already-cataloged
    single-edition titles paired with different patrons than their
    original seed pairing, so each reads as a distinct real request)
  - overdue chasing: 1 RED case (a minor's account, pending approval),
    5 GREEN informational-tier cases (auto-resolved)

Idempotent to run more than once: re-running creates a fresh set of cases
on top of whatever is already there, so run scripts/seed_dynamodb.py first
if you want a clean baseline, then this script once before a demo or
judging session:

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

# Previously-unused room_b/room_a time slots (the existing fixture's
# bookings all sit on 2026-09-01 or 2026-09-03; these are different days
# entirely, so nothing here can collide with them or with each other) --
# keeps every conflict a clean two-way one instead of a confusing
# three-way one.
_RED_SEED_SLOT_START = datetime(2026, 9, 10, 16, 0, tzinfo=timezone.utc)
_RED_SEED_SLOT_END = datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc)
_RED_CONFLICT_SLOT_START = "2026-09-10T16:15:00+00:00"
_RED_CONFLICT_SLOT_END = "2026-09-10T16:45:00+00:00"

_GREEN_CONFLICT_ROOM_ID = "room_a"
_GREEN_CONFLICT_FIRST_START = "2026-09-12T13:00:00+00:00"
_GREEN_CONFLICT_FIRST_END = "2026-09-12T14:00:00+00:00"
_GREEN_CONFLICT_SECOND_START = "2026-09-12T13:15:00+00:00"
_GREEN_CONFLICT_SECOND_END = "2026-09-12T13:45:00+00:00"

_STANDALONE_BOOKINGS = [
    {"roomId": "room_a", "start": "2026-09-12T09:00:00+00:00", "end": "2026-09-12T10:00:00+00:00", "bookingType": "staff_internal", "bookedBy": "Library Programs Team"},
    {"roomId": "room_b", "start": "2026-09-12T10:00:00+00:00", "end": "2026-09-12T11:00:00+00:00", "bookingType": "walk_in", "bookedBy": "Walk-in Patron"},
    {"roomId": "room_a", "start": "2026-09-13T15:00:00+00:00", "end": "2026-09-13T16:00:00+00:00", "bookingType": "one_off_renter", "bookedBy": "Community Book Club"},
]

# Titles already cataloged with exactly one edition each in
# stacks.data.fixtures.seed_demo_library -- reused here with a different
# requester than their original seed pairing, so each live GREEN request
# reads as a distinct case rather than a duplicate of an existing row.
_GREEN_ILL_REQUESTS = [
    {"requestedTitle": "The Hobbit", "requesterPatronId": "patron_ill_1"},
    {"requestedTitle": "Pride and Prejudice", "requesterPatronId": "patron_ill_3"},
    {"requestedTitle": "Beloved", "requesterPatronId": "patron_ill_4"},
]

# Reuses the four named, already-display-mapped overdue patrons
# (bff/display_names.py) paired with a different item than their existing
# seeded record, since a patron having a second item checked out is
# ordinary, not a data inconsistency.
_GREEN_OVERDUE_CASES = [
    {"patronId": "patron_overdue_1", "itemId": "item_2", "itemType": "book", "daysOverdue": 4},
    {"patronId": "patron_overdue_2", "itemId": "item_3", "itemType": "book", "daysOverdue": 6},
    {"patronId": "patron_overdue_3", "itemId": "item_4", "itemType": "book", "daysOverdue": 8},
    {"patronId": "patron_overdue_4", "itemId": "item_1", "itemType": "book", "daysOverdue": 3},
    {"patronId": "patron_overdue_1", "itemId": "item_4", "itemType": "book", "daysOverdue": 5},
]


def _seed_flagged_room_booking() -> None:
    repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    repo.save_booking(BookingRecord(
        booking_id="b_seed_minor_flagged", library_id=LIBRARY_ID, room_id="room_b",
        start=_RED_SEED_SLOT_START, end=_RED_SEED_SLOT_END,
        booked_by="patron_teen_group", booking_type=BookingType.RECURRING_PROGRAM,
        flags=[SensitivityFlag.MINOR_ACCOUNT], notes="Teen manga club",
    ))
    print("Seeded a flagged room_b booking (b_seed_minor_flagged) for the RED conflict scenario.")


def _judge_login(client: httpx.Client) -> str:
    response = client.post(f"{BFF_BASE_URL}/api/auth/judge-login", headers={"Origin": FRONTEND_ORIGIN})
    response.raise_for_status()
    return response.json()["csrfToken"]


def _post(client: httpx.Client, csrf_token: str, path: str, payload: dict) -> dict:
    response = client.post(
        f"{BFF_BASE_URL}{path}",
        headers={"Origin": FRONTEND_ORIGIN, "X-Stacks-CSRF-Token": csrf_token},
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def _create_red_room_conflict(client: httpx.Client, csrf_token: str) -> None:
    body = _post(client, csrf_token, "/api/bookings", {
        "roomId": "room_b", "start": _RED_CONFLICT_SLOT_START, "end": _RED_CONFLICT_SLOT_END,
        "bookingType": "walk_in", "bookedBy": "patron_walkin_seed",
    })
    print(f"Room booking case {body['bookingId']}: status={body['status']} (expect pending_approval, RED)")


def _create_green_room_conflict(client: httpx.Client, csrf_token: str) -> None:
    first = _post(client, csrf_token, "/api/bookings", {
        "roomId": _GREEN_CONFLICT_ROOM_ID, "start": _GREEN_CONFLICT_FIRST_START, "end": _GREEN_CONFLICT_FIRST_END,
        "bookingType": "recurring_program", "bookedBy": "Library Programs Team",
    })
    print(f"Room booking {first['bookingId']}: status={first['status']} (first half of the GREEN pair, expect no_conflict)")
    second = _post(client, csrf_token, "/api/bookings", {
        "roomId": _GREEN_CONFLICT_ROOM_ID, "start": _GREEN_CONFLICT_SECOND_START, "end": _GREEN_CONFLICT_SECOND_END,
        "bookingType": "one_off_renter", "bookedBy": "Community Book Club",
    })
    print(f"Room booking {second['bookingId']}: status={second['status']} (expect resolved, GREEN, auto-committed)")


def _create_standalone_bookings(client: httpx.Client, csrf_token: str) -> None:
    for payload in _STANDALONE_BOOKINGS:
        body = _post(client, csrf_token, "/api/bookings", payload)
        print(f"Room booking {body['bookingId']}: status={body['status']} (expect no_conflict)")


def _create_yellow_ill_case(client: httpx.Client, csrf_token: str) -> None:
    body = _post(client, csrf_token, "/api/ill-requests", {"requestedTitle": "Middlemarch", "requesterPatronId": "patron_ill_2"})
    print(f"ILL routing case {body['illRequestId']}: status={body['status']} (expect pending_approval, YELLOW)")


def _create_green_ill_cases(client: httpx.Client, csrf_token: str) -> None:
    for payload in _GREEN_ILL_REQUESTS:
        body = _post(client, csrf_token, "/api/ill-requests", payload)
        print(f"ILL routing case {body['illRequestId']}: status={body['status']} (expect resolved, GREEN, auto-routed)")


def _create_red_overdue_case(client: httpx.Client, csrf_token: str) -> None:
    body = _post(client, csrf_token, "/api/overdue-cases", {
        "patronId": "patron_overdue_4", "itemId": "item_seed_overdue",
        "itemType": "book", "daysOverdue": 45, "sensitivityFlag": True,
    })
    print(f"Overdue case {body['circulationRecordId']}: status={body['status']} (expect pending_approval, RED)")


def _create_green_overdue_cases(client: httpx.Client, csrf_token: str) -> None:
    for payload in _GREEN_OVERDUE_CASES:
        body = _post(client, csrf_token, "/api/overdue-cases", {**payload, "sensitivityFlag": False})
        print(f"Overdue case {body['circulationRecordId']}: status={body['status']} (expect resolved, GREEN, auto-committed)")


def main() -> None:
    if not BFF_BASE_URL:
        print("STACKS_BFF_BASE_URL must be set to the live BFF's base URL.", file=sys.stderr)
        raise SystemExit(1)

    _seed_flagged_room_booking()

    with httpx.Client(timeout=30.0) as client:
        csrf_token = _judge_login(client)

        _create_red_room_conflict(client, csrf_token)
        _create_green_room_conflict(client, csrf_token)
        _create_standalone_bookings(client, csrf_token)

        _create_yellow_ill_case(client, csrf_token)
        _create_green_ill_cases(client, csrf_token)

        _create_red_overdue_case(client, csrf_token)
        _create_green_overdue_cases(client, csrf_token)

    print("Done. RED and YELLOW cases are left pending for a judge to review and approve themselves.")


if __name__ == "__main__":
    main()
