"""MemoryStore protocol and in-memory implementation for the two
AgentCore Memory long-term strategies. See
docs/architecture/agent_architecture.md section 4.4 for the exact
namespace/trigger/failure-mode contract this protocol exists to satisfy.

Namespace is always the composite (library_id, entity_id) tuple, never a
bare entity_id -- the same cross-tenant-leak discipline TierLedger and
EvaluationCache already apply (Plan 1 Tasks 8-9).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from stacks.types import HardshipHistoryFact, LibraryId, PatronId, RequesterSubstitutionPattern


class MemoryStore(Protocol):
    def get_ill_substitution_pattern(
        self, library_id: LibraryId, requester_key: str
    ) -> RequesterSubstitutionPattern | None: ...

    def record_ill_routing_event(
        self,
        library_id: LibraryId,
        requester_key: str,
        request_frequency_delta: int,
        subject_area: str | None,
        resolved_via_substitution: bool,
    ) -> None: ...

    def get_hardship_history(
        self, library_id: LibraryId, patron_id: PatronId
    ) -> HardshipHistoryFact | None: ...

    def record_hardship_flag(self, library_id: LibraryId, patron_id: PatronId, flagged_at) -> None: ...


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._ill_patterns: dict[tuple[str, str], RequesterSubstitutionPattern] = {}
        self._hardship_facts: dict[tuple[str, str], HardshipHistoryFact] = {}

    def get_ill_substitution_pattern(
        self, library_id: LibraryId, requester_key: str
    ) -> RequesterSubstitutionPattern | None:
        return self._ill_patterns.get((library_id, requester_key))

    def set_ill_substitution_pattern(
        self, library_id: LibraryId, requester_key: str, pattern: RequesterSubstitutionPattern
    ) -> None:
        """Test/fixture-only helper -- not part of the protocol."""
        self._ill_patterns[(library_id, requester_key)] = pattern

    def record_ill_routing_event(
        self,
        library_id: LibraryId,
        requester_key: str,
        request_frequency_delta: int,
        subject_area: str | None,
        resolved_via_substitution: bool,
    ) -> None:
        existing = self._ill_patterns.get((library_id, requester_key))
        frequency = (existing.request_frequency if existing else 0) + request_frequency_delta
        subject_areas = list(existing.subject_areas) if existing else []
        if subject_area and subject_area not in subject_areas:
            subject_areas.append(subject_area)
        accepted = (existing.has_accepted_substitution_without_escalation if existing else False) or resolved_via_substitution
        self._ill_patterns[(library_id, requester_key)] = RequesterSubstitutionPattern(
            request_frequency=frequency, subject_areas=subject_areas,
            has_accepted_substitution_without_escalation=accepted,
            last_updated=datetime.now(timezone.utc),
        )

    def get_hardship_history(self, library_id: LibraryId, patron_id: PatronId) -> HardshipHistoryFact | None:
        return self._hardship_facts.get((library_id, patron_id))

    def set_hardship_history(self, library_id: LibraryId, patron_id: PatronId, fact: HardshipHistoryFact) -> None:
        """Test/fixture-only helper -- not part of the protocol."""
        self._hardship_facts[(library_id, patron_id)] = fact

    def record_hardship_flag(self, library_id: LibraryId, patron_id: PatronId, flagged_at) -> None:
        self._hardship_facts[(library_id, patron_id)] = HardshipHistoryFact(flagged_at=flagged_at)
