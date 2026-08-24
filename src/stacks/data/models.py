"""Domain records backing the synthetic library-operations dataset.

Field shapes mirror docs/architecture/tool_architecture.md section 3.1's
output schemas exactly (RoomCalendarResult.BookingRecord,
ILLQueueResult.ILLRequestRecord, CirculationRecordResult.CirculationRecord).
"""
from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field

from stacks.types import (
    BookingId,
    CirculationRecordId,
    HoldingId,
    ILLRequestId,
    LibraryId,
    PatronId,
    SensitivityFlag,
)


class BookingType(str, enum.Enum):
    RECURRING_PROGRAM = "recurring_program"
    ONE_OFF_RENTER = "one_off_renter"
    STAFF_INTERNAL = "staff_internal"
    WALK_IN = "walk_in"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING_CONFLICT = "pending_conflict"


class BookingRecord(BaseModel):
    booking_id: BookingId
    library_id: LibraryId
    room_id: str
    start: datetime
    end: datetime
    booked_by: PatronId
    booking_type: BookingType
    status: BookingStatus = BookingStatus.CONFIRMED
    flags: list[SensitivityFlag] = Field(default_factory=list)
    notes: str = ""


class ILLRequestStatus(str, enum.Enum):
    OPEN = "open"
    ROUTED = "routed"
    NO_MATCH = "no_match"


class ILLRequestRecord(BaseModel):
    ill_request_id: ILLRequestId
    library_id: LibraryId
    requested_title: str
    requested_edition_hint: str | None = None
    requester_patron_id: PatronId
    status: ILLRequestStatus = ILLRequestStatus.OPEN
    flags: list[SensitivityFlag] = Field(default_factory=list)


class CatalogCandidate(BaseModel):
    holding_id: HoldingId
    edition: str
    location: str
    availability: str


class CirculationRecord(BaseModel):
    circulation_record_id: CirculationRecordId
    library_id: LibraryId
    patron_id: PatronId
    item_id: str
    item_type: str
    due_date: datetime
    returned: bool = False
    prior_overdue_incident_count: int = 0
    flags: list[SensitivityFlag] = Field(default_factory=list)
    prior_reminder_tier_sent: int = -1
