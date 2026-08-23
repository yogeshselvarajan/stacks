"""Session-scoped store of the most recent evaluate() result per case,
read by the matching commit() call's closed-world validator.

tool_architecture.md's "evaluate/commit split" requires commit to validate
its chosen outcome against evaluate's own candidate set, not trust the
caller. Plan 1 implements this as an explicit, injected cache rather than
Strands' native invocation_state dict, kept deliberately simple and
directly testable; wiring it to a real per-session invocation_state is a
refinement, not a behavior change, for a later plan.
"""
from __future__ import annotations

from typing import Any


class EvaluationCache:
    def __init__(self) -> None:
        self._by_case: dict[tuple[str, str], dict[str, Any]] = {}

    def put(self, library_id: str, case_id: str, evaluation: dict[str, Any]) -> None:
        self._by_case[(library_id, case_id)] = evaluation

    def get(self, library_id: str, case_id: str) -> dict[str, Any] | None:
        return self._by_case.get((library_id, case_id))
