"""Real AgentCore Memory-backed MemoryStore. See
docs/architecture/agent_architecture.md section 4.4 for the two named
long-term strategies this implements, and this plan's SDK-verification
note for the exact bedrock_agentcore.memory.MemoryClient API this was
verified against (installed version 1.18.1).

Deliberately does not depend on the semantic strategy's own async
extraction to decide what a "distilled fact" means: Stacks' own tool code
computes the reduced fact (frequency count, subject area, hardship flag
presence) before writing, and writes it as a structured JSON message via
create_event. The configured semantic strategy exists for durability and
AgentCore Memory's own summarization value, not as the thing this class
depends on for correctness -- retrieve_memories is asked directly for
matching events, not for the strategy's own consolidated output, so a
correctness-relevant read never blocks on async consolidation timing that
this codebase does not control.

UNVERIFIED (per this plan's SDK-verification note, and confirmed still
unresolved by Task 6): the write-to-read latency of create_event ->
retrieve_memories, and the exact shape of a retrieved event's content
(_extract_json_payload's parsing logic). Neither has been confirmed
against a live call as of this task -- that happens when a human runs
`scripts/provision_agentcore_memory.py` and then the two live tests in
`tests/unit/test_agentcore_memory_store.py` manually. Once run, record the
observed latency and actual content shape here.

KNOWN DISCREPANCY found via local introspection (no network/credentials
needed, `inspect.getsource(MemoryClient.retrieve_memories)` against the
installed bedrock_agentcore==1.18.1 package) and NOT fixed in this task,
per this task's explicit instruction not to silently guess a fix for an
API mismatch: `retrieve_memories`'s `query` parameter is typed with a
default of `None` in its signature, but the method's own body raises
`TypeError("retrieve_memories() missing required argument: 'query'")`
immediately if `query is None`. This module's calls below (as specified
by this plan's brief) do not pass `query`, so as written they will raise
that TypeError before ever reaching AWS, the first time a human runs the
live tests in Step 5 -- this is not a "wrong retrieved shape" problem, it
is a hard call-time error. A plausible fix is to pass some fixed `query`
value (e.g. an empty string, or a project-specific sentinel), but the
correct value depends on AgentCore Memory's real retrieval semantics
(whether an empty/wildcard query still returns all records scoped by
`namespace`/`actor_id`, or returns none) -- semantics this task's
real-AWS boundary does not permit verifying live. Left as specified by
the brief; flagged here and in the Task 6 report for the human running
Step 5 to resolve.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from bedrock_agentcore.memory import MemoryClient

from stacks.types import HardshipHistoryFact, LibraryId, PatronId, RequesterSubstitutionPattern

_ILL_ACTOR_PREFIX = "ill_pattern"
_HARDSHIP_ACTOR_PREFIX = "hardship"


class AgentCoreMemoryStore:
    def __init__(self, memory_id: str, region: str) -> None:
        self._memory_id = memory_id
        self._client = MemoryClient(region_name=region)

    def get_ill_substitution_pattern(
        self, library_id: LibraryId, requester_key: str
    ) -> RequesterSubstitutionPattern | None:
        namespace = f"{library_id}:{requester_key}"
        actor_id = f"{_ILL_ACTOR_PREFIX}:{namespace}"
        events = self._client.retrieve_memories(
            memory_id=self._memory_id, namespace=namespace, actor_id=actor_id, top_k=1,
        )
        if not events:
            return None
        payload = _extract_json_payload(events[0])
        if payload is None:
            return None
        return RequesterSubstitutionPattern(**payload)

    def record_ill_routing_event(
        self,
        library_id: LibraryId,
        requester_key: str,
        request_frequency_delta: int,
        subject_area: str | None,
        resolved_via_substitution: bool,
    ) -> None:
        namespace = f"{library_id}:{requester_key}"
        actor_id = f"{_ILL_ACTOR_PREFIX}:{namespace}"
        existing = self.get_ill_substitution_pattern(library_id, requester_key)
        frequency = (existing.request_frequency if existing else 0) + request_frequency_delta
        subject_areas = list(existing.subject_areas) if existing else []
        if subject_area and subject_area not in subject_areas:
            subject_areas.append(subject_area)
        accepted = (existing.has_accepted_substitution_without_escalation if existing else False) or resolved_via_substitution
        pattern = RequesterSubstitutionPattern(
            request_frequency=frequency, subject_areas=subject_areas,
            has_accepted_substitution_without_escalation=accepted,
            last_updated=datetime.now(timezone.utc),
        )
        self._client.create_event(
            memory_id=self._memory_id, actor_id=actor_id, session_id=namespace,
            messages=[(json.dumps(pattern.model_dump(mode="json")), "ASSISTANT")],
        )

    def get_hardship_history(self, library_id: LibraryId, patron_id: PatronId) -> HardshipHistoryFact | None:
        namespace = f"{library_id}:{patron_id}"
        actor_id = f"{_HARDSHIP_ACTOR_PREFIX}:{namespace}"
        events = self._client.retrieve_memories(
            memory_id=self._memory_id, namespace=namespace, actor_id=actor_id, top_k=1,
        )
        if not events:
            return None
        payload = _extract_json_payload(events[0])
        if payload is None:
            return None
        return HardshipHistoryFact(**payload)

    def record_hardship_flag(self, library_id: LibraryId, patron_id: PatronId, flagged_at: datetime) -> None:
        namespace = f"{library_id}:{patron_id}"
        actor_id = f"{_HARDSHIP_ACTOR_PREFIX}:{namespace}"
        fact = HardshipHistoryFact(flagged_at=flagged_at)
        self._client.create_event(
            memory_id=self._memory_id, actor_id=actor_id, session_id=namespace,
            messages=[(json.dumps(fact.model_dump(mode="json")), "ASSISTANT")],
        )


def _extract_json_payload(event: dict) -> dict | None:
    """Extract this store's own JSON-serialized fact from a retrieved
    memory event's content. The exact key path returned by
    retrieve_memories was not confirmed by static inspection alone (see
    this plan's SDK-verification note) -- verify against a real retrieved
    event in Step 5 and adjust this function's shape-checking to match
    what is actually returned, updating this docstring with what was
    found.
    """
    try:
        content = event.get("content") or event.get("memory", {}).get("content")
        if isinstance(content, str):
            return json.loads(content)
        if isinstance(content, dict) and "text" in content:
            return json.loads(content["text"])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    return None
