"""PendingApprovals -- the queryable record of "this case is waiting on a
human". Today, that fact only exists implicitly, inside a paused agent
session's own interrupt state -- nothing queryable records it, so the
Approval Inbox (docs/architecture/frontend_architecture.md section 7.3)
cannot list pending cases without this.

HitlGateHook (Task 3) writes a record the moment it raises a real
interrupt. The BFF's write/resume endpoint (Task 17) deletes the record
once the interrupt is actually resolved. Mirrors AuditLogRecord/
AuditLogSink (src/stacks/hooks/audit_log.py) exactly: a plain record, a
Protocol, and an in-memory default implementation.
"""
from __future__ import annotations

from typing import Any, Protocol


class PendingApprovalRecord:
    __slots__ = (
        "library_id", "case_id", "tier", "tool", "workflow", "reason",
        "interrupt_id", "session_id", "created_at",
    )

    def __init__(self, **kwargs: Any) -> None:
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot))

    def to_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class PendingApprovalsSink(Protocol):
    def put(self, record: PendingApprovalRecord) -> None: ...
    def delete(self, library_id: str, case_id: str) -> None: ...
    def list_for_library(self, library_id: str) -> list[PendingApprovalRecord]: ...


class InMemoryPendingApprovalsSink:
    def __init__(self) -> None:
        self._by_case: dict[tuple[str, str], PendingApprovalRecord] = {}

    def put(self, record: PendingApprovalRecord) -> None:
        self._by_case[(record.library_id, record.case_id)] = record

    def delete(self, library_id: str, case_id: str) -> None:
        self._by_case.pop((library_id, case_id), None)

    def list_for_library(self, library_id: str) -> list[PendingApprovalRecord]:
        return [r for (lib, _), r in self._by_case.items() if lib == library_id]
