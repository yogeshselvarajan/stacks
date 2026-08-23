"""Seed data for local development and tests. Not the production dataset --
see docs/architecture/data_model.md for the full, evidence-grounded schema
the AWS-infrastructure follow-on plan implements against DynamoDB.
"""
from __future__ import annotations

from datetime import datetime, timezone

from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.data.models import (
    BookingRecord,
    BookingType,
    CatalogCandidate,
    CirculationRecord,
    ILLRequestRecord,
)
from stacks.types import PolicyClauseRef, SensitivityFlag


def seed_demo_library(repo: InMemoryLibraryDataRepository, library_id: str = "lib_demo") -> None:
    """Populates a small, internally consistent dataset covering:
    a GREEN room-booking conflict (room_a), a RED room-booking conflict
    (room_b, a minor's booking), an unambiguous ILL request, an
    ambiguous multiple-editions ILL request, a GREEN overdue record, and
    a RED (collections_referral-eligible) overdue record.
    """
    # -- Room booking: GREEN case (no sensitivity flags) --
    repo.save_booking(BookingRecord(
        booking_id="b_recurring_a", library_id=library_id, room_id="room_a",
        start=datetime(2026, 9, 1, 10, tzinfo=timezone.utc), end=datetime(2026, 9, 1, 11, tzinfo=timezone.utc),
        booked_by="patron_recurring", booking_type=BookingType.RECURRING_PROGRAM,
        notes="Weekly storytime",
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_oneoff_a", library_id=library_id, room_id="room_a",
        start=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc), end=datetime(2026, 9, 1, 11, 30, tzinfo=timezone.utc),
        booked_by="patron_renter", booking_type=BookingType.ONE_OFF_RENTER,
        notes="Book club, one-time",
    ))

    # -- Room booking: RED case (a minor's booking is involved) --
    repo.save_booking(BookingRecord(
        booking_id="b_recurring_b", library_id=library_id, room_id="room_b",
        start=datetime(2026, 9, 3, 14, tzinfo=timezone.utc), end=datetime(2026, 9, 3, 15, tzinfo=timezone.utc),
        booked_by="patron_teen_group", booking_type=BookingType.RECURRING_PROGRAM,
        flags=[SensitivityFlag.MINOR_ACCOUNT], notes="Teen coding club",
    ))
    repo.save_booking(BookingRecord(
        booking_id="b_walkin_b", library_id=library_id, room_id="room_b",
        start=datetime(2026, 9, 3, 14, 30, tzinfo=timezone.utc), end=datetime(2026, 9, 3, 15, 30, tzinfo=timezone.utc),
        booked_by="patron_walkin", booking_type=BookingType.WALK_IN,
    ))

    repo.set_policy_clauses(library_id, "room_booking_priority", [
        PolicyClauseRef(
            policy_name="room_booking_priority",
            clause_id="RBP-1",
            clause_text="A recurring, library-run program outranks a one-off renter or walk-in booking for the same slot.",
        ),
    ])

    # -- ILL: unambiguous case --
    repo.save_ill_request(ILLRequestRecord(
        ill_request_id="ill_unambiguous", library_id=library_id,
        requested_title="The Structure of Scientific Revolutions",
        requester_patron_id="patron_ill_1",
    ))
    repo.set_catalog_candidates(library_id, "The Structure of Scientific Revolutions", [
        CatalogCandidate(holding_id="hold_1", edition="1st", location="lib_partner_a", availability="available"),
    ])

    # -- ILL: ambiguous multiple-editions case --
    repo.save_ill_request(ILLRequestRecord(
        ill_request_id="ill_ambiguous", library_id=library_id,
        requested_title="Middlemarch",
        requester_patron_id="patron_ill_2",
    ))
    repo.set_catalog_candidates(library_id, "Middlemarch", [
        CatalogCandidate(holding_id="hold_2a", edition="Penguin Classics", location="lib_partner_a", availability="available"),
        CatalogCandidate(holding_id="hold_2b", edition="Oxford World's Classics", location="lib_partner_b", availability="available"),
    ])

    repo.set_policy_clauses(library_id, "ill_routing", [
        PolicyClauseRef(
            policy_name="ill_routing", clause_id="ILL-1",
            clause_text="When multiple editions are available and none is specified, route to the nearest partner library holding an available copy.",
        ),
    ])

    # -- Overdue: GREEN case (informational tier) --
    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_green", library_id=library_id,
        patron_id="patron_overdue_1", item_id="item_1", item_type="book",
        due_date=datetime(2026, 8, 20, tzinfo=timezone.utc),
    ))

    # -- Overdue: RED case (already at the top of the ladder) --
    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_red", library_id=library_id,
        patron_id="patron_overdue_2", item_id="item_2", item_type="book",
        due_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        prior_reminder_tier_sent=3,
    ))

    repo.set_policy_clauses(library_id, "overdue_escalation", [
        PolicyClauseRef(
            policy_name="overdue_escalation", clause_id="OD-1",
            clause_text="Escalate through informational, fee_mention, hold_block, then collections_referral, one tier per contact, never skipping a tier.",
        ),
    ])
