"""Records the HITL tier each committed action was classified at, so
notify_parties can validate its own approval_token against that same tier
without recomputing classify() a second time (tool_architecture.md
section 3.5's Authorization boundary).
"""
from __future__ import annotations

from stacks.hitl.classify import Tier, Workflow


class TierLedger:
    def __init__(self) -> None:
        self._by_action_id: dict[str, tuple[Tier, Workflow]] = {}

    def record(self, related_action_id: str, tier: Tier, workflow: Workflow) -> None:
        self._by_action_id[related_action_id] = (tier, workflow)

    def get(self, related_action_id: str) -> tuple[Tier, Workflow] | None:
        return self._by_action_id.get(related_action_id)
