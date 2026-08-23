"""get_library_data -- deterministic, read-only access to the synthetic
library-operations dataset. See docs/architecture/tool_architecture.md
section 3.1 for the full spec this implements.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from strands import tool

from stacks.data.repository import LibraryDataRepository

MAX_RESULTS = 50


def make_get_library_data(repo: LibraryDataRepository, session_library_id: str):
    """Build the get_library_data tool bound to one repository and one
    session's Identity-sourced library_id.

    Returned as a closure, not a bare module-level function, because the
    tool must be scoped to the invoking session's library_id --
    tool_architecture.md section 3.1's Authorization boundary.
    """

    @tool
    def get_library_data(
        library_id: str,
        query_type: str,
        room_calendar_filter: dict[str, Any] | None = None,
        ill_queue_filter: dict[str, Any] | None = None,
        circulation_filter: dict[str, Any] | None = None,
        policy_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Read-only access to the room-booking calendar, ILL queue,
        circulation/overdue records, and policy documents.

        Args:
            library_id: The tenant this query is scoped to. Must match the
                session's own library_id or the call is refused.
            query_type: One of "room_calendar", "ill_queue",
                "circulation_record", "policy_document".
            room_calendar_filter: Required when query_type is
                "room_calendar". Shape: room_id, start, end (ISO datetime strings).
            ill_queue_filter: Required when query_type is "ill_queue".
                Shape: ill_request_id.
            circulation_filter: Required when query_type is
                "circulation_record". Shape: circulation_record_id.
            policy_filter: Required when query_type is "policy_document".
                Shape: policy_name.

        Returns:
            A dict discriminated by query_type. See
            docs/architecture/tool_architecture.md section 3.1 for the
            full per-query_type result shape.
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": f"cross_tenant_denied: session is scoped to {session_library_id!r}"}]}

        if query_type == "room_calendar":
            if not room_calendar_filter or "room_id" not in room_calendar_filter:
                return {"status": "error", "content": [{"text": "invalid_filter: room_calendar_filter requires room_id, start, end"}]}
            try:
                start = datetime.fromisoformat(room_calendar_filter["start"])
                end = datetime.fromisoformat(room_calendar_filter["end"])
            except (ValueError, KeyError):
                return {"status": "error", "content": [{"text": "invalid_filter: start and end must be valid ISO datetime strings"}]}
            if start >= end:
                return {"status": "error", "content": [{"text": "invalid_filter: start must be before end"}]}
            bookings = repo.get_bookings_for_room(library_id, room_calendar_filter["room_id"], start, end)
            return {"status": "success", "content": [{"json": {"bookings": [b.model_dump(mode="json") for b in bookings][:MAX_RESULTS]}}]}

        if query_type == "ill_queue":
            if not ill_queue_filter or "ill_request_id" not in ill_queue_filter:
                return {"status": "error", "content": [{"text": "invalid_filter: ill_queue_filter requires ill_request_id"}]}
            request = repo.get_ill_request(library_id, ill_queue_filter["ill_request_id"])
            if request is None:
                return {"status": "error", "content": [{"text": "not_found: no ILL request with that id"}]}
            return {"status": "success", "content": [{"json": {"request": request.model_dump(mode="json")}}]}

        if query_type == "circulation_record":
            if not circulation_filter or "circulation_record_id" not in circulation_filter:
                return {"status": "error", "content": [{"text": "invalid_filter: circulation_filter requires circulation_record_id"}]}
            record = repo.get_circulation_record(library_id, circulation_filter["circulation_record_id"])
            if record is None:
                return {"status": "error", "content": [{"text": "not_found: no circulation record with that id"}]}
            return {"status": "success", "content": [{"json": {"record": record.model_dump(mode="json")}}]}

        if query_type == "policy_document":
            if not policy_filter or "policy_name" not in policy_filter:
                return {"status": "error", "content": [{"text": "invalid_filter: policy_filter requires policy_name"}]}
            clauses = repo.get_policy_clauses(library_id, policy_filter["policy_name"])
            if not clauses:
                return {"status": "error", "content": [{"text": "not_found: no policy document with that name"}]}
            return {"status": "success", "content": [{"json": {"clauses": [c.model_dump(mode="json") for c in clauses][:MAX_RESULTS]}}]}

        return {"status": "error", "content": [{"text": f"invalid_query_type: {query_type!r}"}]}

    return get_library_data
