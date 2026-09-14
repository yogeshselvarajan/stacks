from datetime import datetime, timezone

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.data.models import BookingRecord, BookingType, CirculationRecord


def test_seed_demo_library_populates_a_room_conflict_pair():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")

    bookings = repo.get_bookings_for_room(
        "lib_demo", "room_a",
        datetime(2026, 9, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    assert len(bookings) == 2
    types = {b.booking_type for b in bookings}
    assert types == {BookingType.RECURRING_PROGRAM, BookingType.ONE_OFF_RENTER}


def test_seed_demo_library_populates_a_sensitivity_flagged_conflict():
    from stacks.types import SensitivityFlag

    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")

    bookings = repo.get_bookings_for_room(
        "lib_demo", "room_b",
        datetime(2026, 9, 3, tzinfo=timezone.utc),
        datetime(2026, 9, 4, tzinfo=timezone.utc),
    )
    assert any(SensitivityFlag.MINOR_ACCOUNT in b.flags for b in bookings)


def test_save_booking_round_trips():
    repo = InMemoryLibraryDataRepository()
    booking = BookingRecord(
        booking_id="b_test",
        library_id="lib_demo",
        room_id="room_a",
        start=datetime(2026, 9, 5, tzinfo=timezone.utc),
        end=datetime(2026, 9, 5, 1, tzinfo=timezone.utc),
        booked_by="patron_1",
        booking_type=BookingType.WALK_IN,
    )
    repo.save_booking(booking)
    assert repo.get_booking("lib_demo", "b_test") == booking


def test_policy_clauses_are_seeded_for_all_three_policies():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    for policy_name in ("room_booking_priority", "ill_routing", "overdue_escalation"):
        clauses = repo.get_policy_clauses("lib_demo", policy_name)
        assert len(clauses) >= 1
        assert clauses[0].clause_id


def test_cancelled_booking_does_not_participate_in_a_later_overlap_query():
    from stacks.data.models import BookingStatus

    repo = InMemoryLibraryDataRepository()
    booking = BookingRecord(
        booking_id="b_cancel_test", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 9, 10, tzinfo=timezone.utc), end=datetime(2026, 9, 10, 1, tzinfo=timezone.utc),
        booked_by="patron_1", booking_type=BookingType.WALK_IN,
    )
    repo.save_booking(booking)
    booking.status = BookingStatus.CANCELLED
    repo.save_booking(booking)

    bookings = repo.get_bookings_for_room(
        "lib_demo", "room_a",
        datetime(2026, 9, 10, tzinfo=timezone.utc), datetime(2026, 9, 10, 2, tzinfo=timezone.utc),
    )
    assert bookings == []


def test_delete_booking_removes_the_record():
    repo = InMemoryLibraryDataRepository()
    repo.save_booking(BookingRecord(
        booking_id="b_test_delete", library_id="lib_demo", room_id="room_a",
        start=datetime(2026, 9, 1, 10, tzinfo=timezone.utc), end=datetime(2026, 9, 1, 11, tzinfo=timezone.utc),
        booked_by="patron_x", booking_type=BookingType.ONE_OFF_RENTER,
    ))
    repo.delete_booking("lib_demo", "b_test_delete")
    assert repo.get_booking("lib_demo", "b_test_delete") is None


def test_delete_circulation_record_removes_the_record():
    repo = InMemoryLibraryDataRepository()
    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_test_delete", library_id="lib_demo",
        patron_id="patron_x", item_id="item_x", item_type="book",
        due_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
    ))
    repo.delete_circulation_record("lib_demo", "circ_test_delete")
    assert repo.get_circulation_record("lib_demo", "circ_test_delete") is None
