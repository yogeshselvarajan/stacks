"""write_audit_log -- Hook-driven, unconditional audit trail. Never
model-callable. See docs/architecture/tool_architecture.md section 3.6.
"""
from __future__ import annotations

import copy
import itertools
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from strands.hooks import AfterToolCallEvent, HookProvider, HookRegistry

from stacks.hitl.tier_ledger import TierLedger
from stacks.types import AuditActor

logger = logging.getLogger(__name__)

_MUTATING_TOOLS = {"resolve_room_conflict", "route_ill_request", "run_overdue_chase", "notify_parties"}
_SENSITIVE_INPUT_KEYS = {"rationale", "message_body", "body", "subject"}


class AuditLogRecord:
    __slots__ = (
        "audit_id", "sequence", "tool_name", "tool_input", "tool_output_status", "outcome",
        "session_id", "library_id", "actor", "actor_identity", "timestamp",
        "hitl_tier", "notification_id",
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
    conditional skip branch."

    Fail-closed behavior: If the audit write itself fails, this hook rewrites
    the tool's reported outcome to an error so neither the model nor the
    caller treats the action as recorded. This does not roll back a mutation
    the tool already performed. AfterToolCallEvent fires after the tool has
    returned, so no hook on this event can undo a repository write that
    already landed. A genuinely transactional fail-closed audit would require
    the write to happen inside each tool's own commit path; that is out of
    scope for this hook.
    """

    def __init__(
        self,
        sink: AuditLogSink,
        session_id: str,
        library_id: str,
        tier_ledger: TierLedger | None = None,
    ) -> None:
        self._sink = sink
        self._session_id = session_id
        self._library_id = library_id
        self._tier_ledger = tier_ledger

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._record)

    def _record(self, event) -> None:
        tool_name = event.tool_use["name"]
        if tool_name not in _MUTATING_TOOLS:
            return

        tool_input = event.tool_use["input"]
        status = "error" if event.exception is not None else event.result.get("status", "error")
        outcome = _extract_outcome(event.result, status)

        # Detect human vs agent based on approval_token
        approval_token = tool_input.get("approval_token")
        actor = AuditActor.HUMAN if (isinstance(approval_token, dict) and approval_token.get("approver_role")) else AuditActor.AGENT
        actor_identity = approval_token.get("approver_role") if isinstance(approval_token, dict) else None

        hitl_tier = None
        if self._tier_ledger is not None:
            try:
                related_action_id = _related_action_id_for_audit(tool_name, tool_input)
                if related_action_id is not None:
                    entry = self._tier_ledger.get(self._library_id, related_action_id)
                    if entry is not None:
                        hitl_tier = entry[0].value
            except Exception:
                logger.exception("hitl_tier_lookup_failed")
                hitl_tier = None

        record = AuditLogRecord(
            audit_id=str(uuid.uuid4()),
            tool_name=tool_name,
            tool_input=_sanitize(tool_input),
            tool_output_status=status,
            outcome=outcome,
            session_id=self._session_id,
            library_id=self._library_id,
            actor=actor,
            actor_identity=actor_identity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hitl_tier=hitl_tier,
            notification_id=_extract_notification_id(event.result),
        )
        try:
            self._sink.append(record)
        except Exception:
            logger.exception("audit_write_failed")
            tool_use_id = event.tool_use.get("toolUseId")
            event.result = {"toolUseId": tool_use_id, "status": "error", "content": [{"text": "audit_write_failed: action not recorded"}]}


def _extract_outcome(result: dict[str, Any], fallback_status: str) -> str:
    """Extract the true outcome from the nested tool result JSON.

    resolve_room_conflict and similar tools return envelope status: "success"
    for both real commits and HITL-blocked outcomes. The true outcome lives
    in result["content"][0]["json"]["status"].
    """
    try:
        if (isinstance(result, dict) and "content" in result and
            isinstance(result["content"], list) and len(result["content"]) > 0 and
            isinstance(result["content"][0], dict) and "json" in result["content"][0]):
            inner_json = result["content"][0]["json"]
            if isinstance(inner_json, dict) and "status" in inner_json:
                return inner_json["status"]
    except (KeyError, IndexError, TypeError):
        pass
    return fallback_status


def _extract_notification_id(result: dict[str, Any]) -> str | None:
    """Extract notify_parties's own notification_id from the nested tool
    result JSON, mirroring _extract_outcome's defensive shape-checking.
    None for every other tool's result, which is correct -- whole-branch
    review Important 3.
    """
    try:
        if (isinstance(result, dict) and "content" in result and
            isinstance(result["content"], list) and len(result["content"]) > 0 and
            isinstance(result["content"][0], dict) and "json" in result["content"][0]):
            inner_json = result["content"][0]["json"]
            if isinstance(inner_json, dict) and "notification_id" in inner_json:
                return inner_json["notification_id"]
    except (KeyError, IndexError, TypeError):
        pass
    return None


def _related_action_id_for_audit(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Derives the related_action_id per tool, matching the exact same
    convention HitlGateHook and each tool already use, so the audit hook
    can look up the tier the action was actually classified at without
    recomputing classify() a second time.
    """
    if tool_name == "resolve_room_conflict":
        ids = tool_input.get("conflicting_booking_ids")
        return "room_conflict:" + ":".join(sorted(ids)) if ids else None
    if tool_name == "route_ill_request":
        rid = tool_input.get("ill_request_id")
        return f"ill_request:{rid}" if rid else None
    if tool_name == "run_overdue_chase":
        cid = tool_input.get("circulation_record_id")
        return f"overdue:{cid}" if cid else None
    if tool_name == "notify_parties":
        return tool_input.get("related_action_id")
    return None


def _sanitize(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Records the fact and parameters of access, never a duplicate copy of
    sensitive field values (tool_architecture.md section 3.1's Auditability
    note, applied to every mutating tool's inputs).

    Strips the raw token value from approval_token while preserving its
    approver_role and related_action_id. Uses deepcopy to avoid aliasing
    mutable objects that other code might still mutate.
    """
    sanitized = {}
    for k, v in tool_input.items():
        if k in _SENSITIVE_INPUT_KEYS:
            continue
        if k == "approval_token" and isinstance(v, dict):
            # Only preserve approver_role and related_action_id, drop the raw token
            sanitized[k] = {
                "approver_role": v.get("approver_role"),
                "related_action_id": v.get("related_action_id"),
            }
        else:
            sanitized[k] = v
    return copy.deepcopy(sanitized)
