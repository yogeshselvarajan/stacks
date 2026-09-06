import os
from datetime import datetime, timezone

import pytest

from stacks.data.models import BookingRecord, BookingType


def _repo():
    environment = os.environ.get("STACKS_TEST_DYNAMODB_ENVIRONMENT")
    if not environment:
        pytest.skip("STACKS_TEST_DYNAMODB_ENVIRONMENT not set -- run infra/'s terraform apply first (Task 1)")
    from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository

    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    return DynamoDBLibraryDataRepository(region=region, environment=environment)


def test_live_save_and_get_booking_round_trips():
    repo = _repo()
    booking = BookingRecord(
        booking_id="b_live_test_1", library_id="lib_test_live", room_id="room_live",
        start=datetime(2030, 1, 1, 10, tzinfo=timezone.utc), end=datetime(2030, 1, 1, 11, tzinfo=timezone.utc),
        booked_by="patron_live", booking_type=BookingType.WALK_IN,
    )
    repo.save_booking(booking)
    fetched = repo.get_booking("lib_test_live", "b_live_test_1")
    assert fetched == booking


def test_live_get_bookings_for_room_uses_the_room_time_gsi():
    repo = _repo()
    booking = BookingRecord(
        booking_id="b_live_test_2", library_id="lib_test_live", room_id="room_live_gsi",
        start=datetime(2030, 2, 1, 10, tzinfo=timezone.utc), end=datetime(2030, 2, 1, 11, tzinfo=timezone.utc),
        booked_by="patron_live", booking_type=BookingType.WALK_IN,
    )
    repo.save_booking(booking)
    results = repo.get_bookings_for_room(
        "lib_test_live", "room_live_gsi",
        datetime(2030, 2, 1, 9, tzinfo=timezone.utc), datetime(2030, 2, 1, 12, tzinfo=timezone.utc),
    )
    assert any(b.booking_id == "b_live_test_2" for b in results)


def test_live_cancelled_booking_is_excluded_from_the_overlap_query():
    from stacks.data.models import BookingStatus

    repo = _repo()
    booking = BookingRecord(
        booking_id="b_live_test_3", library_id="lib_test_live", room_id="room_live_cancel",
        start=datetime(2030, 3, 1, 10, tzinfo=timezone.utc), end=datetime(2030, 3, 1, 11, tzinfo=timezone.utc),
        booked_by="patron_live", booking_type=BookingType.WALK_IN, status=BookingStatus.CANCELLED,
    )
    repo.save_booking(booking)
    results = repo.get_bookings_for_room(
        "lib_test_live", "room_live_cancel",
        datetime(2030, 3, 1, 9, tzinfo=timezone.utc), datetime(2030, 3, 1, 12, tzinfo=timezone.utc),
    )
    assert results == []


def test_live_policy_clauses_round_trip():
    from stacks.types import PolicyClauseRef

    repo = _repo()
    clause = PolicyClauseRef(policy_name="room_booking_priority", clause_id="RBP-LIVE-1", clause_text="Live test clause.")
    repo.set_policy_clauses("lib_test_live", "room_booking_priority", [clause])
    fetched = repo.get_policy_clauses("lib_test_live", "room_booking_priority")
    assert fetched == [clause]


def test_live_catalog_candidates_round_trip():
    from stacks.data.models import CatalogCandidate

    repo = _repo()
    candidate = CatalogCandidate(holding_id="hold_live_1", edition="1st", location="lib_partner_live", availability="available")
    repo.set_catalog_candidates("lib_test_live", "Live Test Title", [candidate])
    fetched = repo.search_catalog_candidates("lib_test_live", "Live Test Title", None)
    assert fetched == [candidate]
