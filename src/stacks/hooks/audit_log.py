"""write_audit_log -- Hook-driven, unconditional audit trail. Never
model-callable. See docs/architecture/tool_architecture.md section 3.6.
"""
from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timezone
from typing import Any

from strands.hooks import AfterToolCallEvent, HookProvider, HookRegistry

_MUTATING_TOOLS = {"resolve_room_conflict", "route_ill_request", "run_overdue_chase", "notify_parties"}
_SENSITIVE_INPUT_KEYS = {"rationale", "message_body", "body"}


class AuditLogRecord:
    __slots__ = (
        "audit_id", "sequence", "tool_name", "tool_input", "tool_output_status",
        "session_id", "library_id", "actor", "actor_identity", "timestamp",
    )

    def __init__(self, **kwargs: Any) -> None:
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot))

    def to_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class AuditLogSink:
    """In-memory, append-only sink for Plan 1. A DynamoDB-backed sink
    satisfying the same append()/all() interface is an AWS-infrastructure
    follow-on task.
    """

    def __init__(self) -> None:
        self._records: list[AuditLogRecord] = []
        self._next_sequence = itertools.count(1)

    def append(self, record: AuditLogRecord) -> None:
        record.sequence = next(self._next_sequence)
        self._records.append(record)

    def all(self) -> list[AuditLogRecord]:
        return list(self._records)


class AuditLogHook(HookProvider):
    """Fires unconditionally on AfterToolCallEvent for every mutating tool.

    tool_architecture.md section 3.6: "every mutating tool call must
    produce exactly one AuditRecord, enforced structurally, with no
    conditional skip branch" and "fail-closed: if the audit write itself
    fails, the mutating action it was meant to record is treated as failed
    too."
    """

    def __init__(self, sink: AuditLogSink, session_id: str, library_id: str) -> None:
        self._sink = sink
        self._session_id = session_id
        self._library_id = library_id

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._record)

    def _record(self, event) -> None:
        tool_name = event.tool_use["name"]
        if tool_name not in _MUTATING_TOOLS:
            return

        status = "error" if event.exception is not None else event.result.get("status", "error")
        record = AuditLogRecord(
            audit_id=str(uuid.uuid4()),
            tool_name=tool_name,
            tool_input=_sanitize(event.tool_use["input"]),
            tool_output_status=status,
            session_id=self._session_id,
            library_id=self._library_id,
            actor="AGENT",
            actor_identity=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        try:
            self._sink.append(record)
        except Exception:
            event.result = {"status": "error", "content": [{"text": "audit_write_failed: action not recorded"}]}


def _sanitize(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Records the fact and parameters of access, never a duplicate copy of
    sensitive field values (tool_architecture.md section 3.1's Auditability
    note, applied to every mutating tool's inputs).
    """
    return {k: v for k, v in tool_input.items() if k not in _SENSITIVE_INPUT_KEYS}
