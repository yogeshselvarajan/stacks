"""In-memory LibraryDataRepository implementation. Plan 1 scope only --
see repository.py for the DynamoDB-backed follow-on seam.
"""
from __future__ import annotations

from datetime import datetime

from stacks.data.models import BookingRecord, BookingStatus, CatalogCandidate, CirculationRecord, ILLRequestRecord
from stacks.types import BookingId, CirculationRecordId, ILLRequestId, LibraryId, PolicyClauseRef


class InMemoryLibraryDataRepository:
    def __init__(self) -> None:
        self._bookings: dict[tuple[str, str], BookingRecord] = {}
        self._ill_requests: dict[tuple[str, str], ILLRequestRecord] = {}
        self._catalog: dict[tuple[str, str], list[CatalogCandidate]] = {}
        self._circulation_records: dict[tuple[str, str], CirculationRecord] = {}
        self._policy_clauses: dict[tuple[str, str], list[PolicyClauseRef]] = {}

    def get_bookings_for_room(
        self, library_id: LibraryId, room_id: str, start: datetime, end: datetime
    ) -> list[BookingRecord]:
        return [
            b for (lib, _), b in self._bookings.items()
            if lib == library_id and b.room_id == room_id and b.status != BookingStatus.CANCELLED
            and b.start < end and start < b.end
        ]

    def get_booking(self, library_id: LibraryId, booking_id: BookingId) -> BookingRecord | None:
        return self._bookings.get((library_id, booking_id))

    def save_booking(self, booking: BookingRecord) -> None:
        self._bookings[(booking.library_id, booking.booking_id)] = booking

    def get_ill_request(self, library_id: LibraryId, ill_request_id: ILLRequestId) -> ILLRequestRecord | None:
        return self._ill_requests.get((library_id, ill_request_id))

    def save_ill_request(self, request: ILLRequestRecord) -> None:
        self._ill_requests[(request.library_id, request.ill_request_id)] = request

    def list_ill_requests(self, library_id: LibraryId) -> list[ILLRequestRecord]:
        return [r for (lib, _), r in self._ill_requests.items() if lib == library_id]

    def set_catalog_candidates(self, library_id: str, title: str, candidates: list[CatalogCandidate]) -> None:
        """Test/fixture-only helper -- not part of the protocol, used by
        fixtures.py to seed what search_catalog_candidates returns."""
        self._catalog[(library_id, title)] = candidates

    def search_catalog_candidates(
        self, library_id: LibraryId, title: str, edition_hint: str | None
    ) -> list[CatalogCandidate]:
        return list(self._catalog.get((library_id, title), []))

    def get_circulation_record(
        self, library_id: LibraryId, circulation_record_id: CirculationRecordId
    ) -> CirculationRecord | None:
        return self._circulation_records.get((library_id, circulation_record_id))

    def save_circulation_record(self, record: CirculationRecord) -> None:
        self._circulation_records[(record.library_id, record.circulation_record_id)] = record

    def list_circulation_records(self, library_id: LibraryId) -> list[CirculationRecord]:
        return [r for (lib, _), r in self._circulation_records.items() if lib == library_id]

    def get_policy_clauses(self, library_id: LibraryId, policy_name: str) -> list[PolicyClauseRef]:
        return list(self._policy_clauses.get((library_id, policy_name), []))

    def set_policy_clauses(self, library_id: LibraryId, policy_name: str, clauses: list[PolicyClauseRef]) -> None:
        """Test/fixture-only helper -- not part of the protocol."""
        self._policy_clauses[(library_id, policy_name)] = clauses
