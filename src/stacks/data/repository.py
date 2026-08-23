"""Repository interface for the synthetic library-operations dataset.

Plan 1 ships an in-memory implementation for local development and tests.
A DynamoDB-backed implementation satisfying this same interface is an
AWS-infrastructure follow-on plan; nothing in stacks.tools or stacks.hitl
should import the in-memory implementation directly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from stacks.data.models import BookingRecord, CatalogCandidate, CirculationRecord, ILLRequestRecord
from stacks.types import BookingId, CirculationRecordId, ILLRequestId, LibraryId, PolicyClauseRef


class LibraryDataRepository(Protocol):
    def get_bookings_for_room(
        self, library_id: LibraryId, room_id: str, start: datetime, end: datetime
    ) -> list[BookingRecord]: ...

    def get_booking(self, library_id: LibraryId, booking_id: BookingId) -> BookingRecord | None: ...

    def save_booking(self, booking: BookingRecord) -> None: ...

    def get_ill_request(self, library_id: LibraryId, ill_request_id: ILLRequestId) -> ILLRequestRecord | None: ...

    def save_ill_request(self, request: ILLRequestRecord) -> None: ...

    def search_catalog_candidates(
        self, library_id: LibraryId, title: str, edition_hint: str | None
    ) -> list[CatalogCandidate]: ...

    def get_circulation_record(
        self, library_id: LibraryId, circulation_record_id: CirculationRecordId
    ) -> CirculationRecord | None: ...

    def save_circulation_record(self, record: CirculationRecord) -> None: ...

    def get_policy_clauses(self, library_id: LibraryId, policy_name: str) -> list[PolicyClauseRef]: ...
