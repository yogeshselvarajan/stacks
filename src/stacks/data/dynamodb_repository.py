"""DynamoDB-backed LibraryDataRepository. Satisfies
stacks.data.repository.LibraryDataRepository exactly -- same method
signatures as InMemoryLibraryDataRepository, so every existing tool works
unmodified. Only Bookings needs a query beyond a direct key lookup
(get_bookings_for_room), served by the room_time_index GSI Task 1 created.

Spaces and Patrons tables (also provisioned by Task 1, per
data_model.md's 8-table schema) are deliberately not read or written
here. No tool method in this codebase needs them yet -- a named, honest
scope decision, not a silent gap.
"""
from __future__ import annotations

from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key

from stacks.data.models import BookingRecord, BookingStatus, CatalogCandidate, CirculationRecord, ILLRequestRecord
from stacks.types import BookingId, CirculationRecordId, ILLRequestId, LibraryId, PolicyClauseRef


def _table_name(base: str, environment: str) -> str:
    return f"Stacks-{base}-{environment}"


class DynamoDBLibraryDataRepository:
    def __init__(self, region: str, environment: str = "dev", boto_session: boto3.Session | None = None) -> None:
        session = boto_session or boto3.Session(region_name=region)
        resource = session.resource("dynamodb", region_name=region)
        self._bookings = resource.Table(_table_name("Bookings", environment))
        self._ill_requests = resource.Table(_table_name("ILLRequests", environment))
        self._items = resource.Table(_table_name("Items", environment))
        self._loans = resource.Table(_table_name("Loans", environment))
        self._policy_rules = resource.Table(_table_name("PolicyRules", environment))

    def get_bookings_for_room(
        self, library_id: LibraryId, room_id: str, start: datetime, end: datetime
    ) -> list[BookingRecord]:
        room_key = f"{library_id}#{room_id}"
        response = self._bookings.query(
            IndexName="room_time_index",
            KeyConditionExpression=Key("room_key").eq(room_key) & Key("start").lt(end.isoformat()),
        )
        results = []
        for item in response.get("Items", []):
            booking = _booking_from_item(item)
            if booking.status != BookingStatus.CANCELLED and booking.end > start:
                results.append(booking)
        return results

    def get_booking(self, library_id: LibraryId, booking_id: BookingId) -> BookingRecord | None:
        response = self._bookings.get_item(Key={"library_id": library_id, "booking_id": booking_id})
        item = response.get("Item")
        return _booking_from_item(item) if item else None

    def save_booking(self, booking: BookingRecord) -> None:
        item = booking.model_dump(mode="json")
        item["room_key"] = f"{booking.library_id}#{booking.room_id}"
        self._bookings.put_item(Item=item)

    def get_ill_request(self, library_id: LibraryId, ill_request_id: ILLRequestId) -> ILLRequestRecord | None:
        response = self._ill_requests.get_item(Key={"library_id": library_id, "ill_request_id": ill_request_id})
        item = response.get("Item")
        return ILLRequestRecord(**item) if item else None

    def save_ill_request(self, request: ILLRequestRecord) -> None:
        self._ill_requests.put_item(Item=request.model_dump(mode="json"))

    def list_ill_requests(self, library_id: LibraryId) -> list[ILLRequestRecord]:
        """library_id is the ILLRequests table's own partition key (see
        get_ill_request's Key= above), so a plain query on it returns every
        request for this library without needing a GSI."""
        response = self._ill_requests.query(KeyConditionExpression=Key("library_id").eq(library_id))
        return [ILLRequestRecord(**item) for item in response.get("Items", [])]

    def search_catalog_candidates(
        self, library_id: LibraryId, title: str, edition_hint: str | None
    ) -> list[CatalogCandidate]:
        response = self._items.get_item(Key={"library_id": library_id, "title": title})
        item = response.get("Item")
        if not item:
            return []
        return [CatalogCandidate(**c) for c in item.get("candidates", [])]

    def set_catalog_candidates(self, library_id: str, title: str, candidates: list[CatalogCandidate]) -> None:
        """Fixture-only helper, mirrors InMemoryLibraryDataRepository's own
        non-Protocol helper of the same name (used by the seed script,
        never by a tool)."""
        self._items.put_item(Item={
            "library_id": library_id, "title": title,
            "candidates": [c.model_dump(mode="json") for c in candidates],
        })

    def get_circulation_record(
        self, library_id: LibraryId, circulation_record_id: CirculationRecordId
    ) -> CirculationRecord | None:
        response = self._loans.get_item(Key={"library_id": library_id, "circulation_record_id": circulation_record_id})
        item = response.get("Item")
        return CirculationRecord(**item) if item else None

    def save_circulation_record(self, record: CirculationRecord) -> None:
        self._loans.put_item(Item=record.model_dump(mode="json"))

    def list_circulation_records(self, library_id: LibraryId) -> list[CirculationRecord]:
        """library_id is the Loans table's own partition key (see
        get_circulation_record's Key= above), so a plain query on it returns
        every circulation record for this library without needing a GSI."""
        response = self._loans.query(KeyConditionExpression=Key("library_id").eq(library_id))
        return [CirculationRecord(**item) for item in response.get("Items", [])]

    def get_policy_clauses(self, library_id: LibraryId, policy_name: str) -> list[PolicyClauseRef]:
        response = self._policy_rules.get_item(Key={"library_id": library_id, "policy_name": policy_name})
        item = response.get("Item")
        if not item:
            return []
        return [PolicyClauseRef(**c) for c in item.get("clauses", [])]

    def set_policy_clauses(self, library_id: LibraryId, policy_name: str, clauses: list[PolicyClauseRef]) -> None:
        self._policy_rules.put_item(Item={
            "library_id": library_id, "policy_name": policy_name,
            "clauses": [c.model_dump(mode="json") for c in clauses],
        })


def _booking_from_item(item: dict) -> BookingRecord:
    item = dict(item)
    item.pop("room_key", None)
    return BookingRecord(**item)
