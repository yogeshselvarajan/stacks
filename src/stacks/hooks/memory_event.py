"""record_memory_event -- Hook-driven, unconditional AgentCore Memory
write. Never model-callable, for the same reason write_audit_log isn't.
See docs/architecture/tool_architecture.md section 3.7 for the two exact
trigger conditions this implements.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from strands.hooks import AfterToolCallEvent, HookProvider, HookRegistry

from stacks.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class MemoryEventHook(HookProvider):
    def __init__(self, store: MemoryStore, library_id: str) -> None:
        self._store = store
        self._library_id = library_id

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._record)

    def _record(self, event) -> None:
        tool_name = event.tool_use["name"]
        if tool_name not in ("route_ill_request", "run_overdue_chase"):
            return

        result_json = _extract_result_json(event.result)
        if result_json is None or result_json.get("status") != "committed":
            return

        try:
            if tool_name == "route_ill_request":
                self._record_ill_pattern(result_json)
            else:
                self._record_hardship_flag(result_json)
        except Exception:
            logger.exception("record_memory_event_failed")
            tool_use_id = event.tool_use.get("toolUseId")
            event.result = {
                "toolUseId": tool_use_id, "status": "error",
                "content": [{"text": "memory_write_failed: action not recorded"}],
            }

    def _record_ill_pattern(self, result_json: dict[str, Any]) -> None:
        requester_key = result_json.get("requester_patron_id")
        if not requester_key:
            return
        self._store.record_ill_routing_event(
            self._library_id, requester_key,
            request_frequency_delta=1,
            subject_area=result_json.get("subject_area"),
            resolved_via_substitution=bool(result_json.get("resolved_via_substitution")),
        )

    def _record_hardship_flag(self, result_json: dict[str, Any]) -> None:
        if result_json.get("hitl_tier") != "RED":
            return
        if "HARDSHIP_PATTERN" not in (result_json.get("sensitivity_flags") or []):
            return
        patron_id = result_json.get("patron_id")
        if not patron_id:
            return
        self._store.record_hardship_flag(self._library_id, patron_id, flagged_at=datetime.now(timezone.utc))


def _extract_result_json(result: dict[str, Any]) -> dict[str, Any] | None:
    """Same defensive shape-check as stacks.hooks.audit_log._extract_outcome,
    duplicated deliberately rather than imported -- this hook must not
    depend on AuditLogHook's internals, only on the same public tool-result
    envelope shape both hooks read.
    """
    try:
        if (isinstance(result, dict) and "content" in result and
            isinstance(result["content"], list) and len(result["content"]) > 0 and
            isinstance(result["content"][0], dict) and "json" in result["content"][0]):
            inner = result["content"][0]["json"]
            if isinstance(inner, dict):
                return inner
    except (KeyError, IndexError, TypeError):
        pass
    return None
