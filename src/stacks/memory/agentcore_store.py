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
installed bedrock_agentcore==1.18.1 package): `retrieve_memories`'s
`query` parameter is typed with a default of `None` in its signature, but
the method's own body raises
`TypeError("retrieve_memories() missing required argument: 'query'")`
immediately if `query is None`. This is fully knowable and fully fixable
from local introspection alone (no AWS access needed), unlike the
retrieved-event-shape question above, which genuinely requires a live
response to resolve -- so both `retrieve_memories` calls below now pass
an explicit `query=actor_id`. This avoids the guaranteed call-time
TypeError (which, since `get_ill_substitution_pattern` is also called
internally by `record_ill_routing_event` to read existing state before
merging, previously made all 4 public methods on this class unusable, not
just the two read methods). What remains genuinely unverified until a
human runs Step 5's live test is the *semantic* correctness of
`query=actor_id`: whether AgentCore Memory's retrieval actually scopes
results by `namespace`/`actor_id` regardless of `query` content (in which
case any non-empty string works), or whether `query` is matched
semantically against event content (in which case `actor_id`, which never
appears in the JSON payload written by this class, may fail to match
anything). Record what Step 5 observes here once run.

One more item worth flagging while already reading this section of the
SDK: `retrieve_memories`'s own docstring marks its `actor_id` parameter
"(deprecated, use namespace)". This module still passes both `namespace`
and `actor_id` to every call, matching the brief's original design and
not itself a call-time break, but a future reader should know `actor_id`
alongside `namespace` is passing a deprecated parameter, not an
oversight -- worth revisiting when this is next touched.

NAMESPACE CONVENTION (whole-branch review Important 6, fixed 2026-08-24):
this module and scripts/provision_agentcore_memory.py previously
disagreed on the namespace convention -- the provisioning script
configured strategy namespace templates as "/ill_pattern/{actorId}" and
"/hardship/{actorId}", while this module queried retrieve_memories with a
plain "{library_id}:{requester_key}" namespace and a SEPARATELY-prefixed
"{workflow}:{namespace}" actor_id. Resolving the provisioning script's
template against that actor_id would produce something like
"/ill_pattern/ill_pattern:lib_demo:patron_1", which can never equal the
plain namespace string this module queried with -- a self-inconsistency
between two files written in the same task, checkable statically by
reading `MemoryClient.add_semantic_strategy`'s own docstring and source
(`inspect.getsource`), no AWS call needed.

The reconciled convention, now used consistently by both files: namespace
IS actor_id IS one single composite string,
f"{workflow_prefix}:{library_id}:{entity_key}" (e.g.
"ill_pattern:lib_demo:patron_1"), computed once per method below and
passed unchanged to every namespace/actor_id/query parameter. The
provisioning script's strategies now use namespace_templates=["{actorId}"]
(the AgentCore Memory template placeholder that resolves to exactly the
create_event actor_id passed at write time, with no additional path
segments) -- since the workflow prefix already lives inside the actor_id
string itself, the two strategies' templates do not need to differ, and
the two workflows' namespaces can never collide with each other or across
library_id/entity_key (same discipline TierLedger and EvaluationCache
already apply). This also switches the provisioning script from the
deprecated `namespaces=` kwarg to `namespace_templates=`
(confirmed via `inspect.getdoc(MemoryClient.add_semantic_strategy)`: the
former is documented "DEPRECATED. Use ``namespace_templates`` instead.").
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from bedrock_agentcore.memory import MemoryClient

from stacks.types import HardshipHistoryFact, LibraryId, PatronId, RequesterSubstitutionPattern

_ILL_ACTOR_PREFIX = "ill_pattern"
_HARDSHIP_ACTOR_PREFIX = "hardship"


def _ill_namespace(library_id: LibraryId, requester_key: str) -> str:
    """The one composite string used as namespace, actor_id, and query for
    every ILL substitution-pattern call -- see this module's own
    NAMESPACE CONVENTION note above. Must match
    scripts/provision_agentcore_memory.py's namespace_templates=["{actorId}"]
    resolution exactly.
    """
    return f"{_ILL_ACTOR_PREFIX}:{library_id}:{requester_key}"


def _hardship_namespace(library_id: LibraryId, patron_id: PatronId) -> str:
    """The hardship-history counterpart to _ill_namespace above."""
    return f"{_HARDSHIP_ACTOR_PREFIX}:{library_id}:{patron_id}"


class AgentCoreMemoryStore:
    def __init__(self, memory_id: str, region: str) -> None:
        self._memory_id = memory_id
        self._client = MemoryClient(region_name=region)

    def get_ill_substitution_pattern(
        self, library_id: LibraryId, requester_key: str
    ) -> RequesterSubstitutionPattern | None:
        namespace = _ill_namespace(library_id, requester_key)
        events = self._client.retrieve_memories(
            memory_id=self._memory_id, namespace=namespace, actor_id=namespace, query=namespace, top_k=1,
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
        namespace = _ill_namespace(library_id, requester_key)
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
            memory_id=self._memory_id, actor_id=namespace, session_id=f"{library_id}:{requester_key}",
            messages=[(json.dumps(pattern.model_dump(mode="json")), "ASSISTANT")],
        )

    def get_hardship_history(self, library_id: LibraryId, patron_id: PatronId) -> HardshipHistoryFact | None:
        namespace = _hardship_namespace(library_id, patron_id)
        events = self._client.retrieve_memories(
            memory_id=self._memory_id, namespace=namespace, actor_id=namespace, query=namespace, top_k=1,
        )
        if not events:
            return None
        payload = _extract_json_payload(events[0])
        if payload is None:
            return None
        return HardshipHistoryFact(**payload)

    def record_hardship_flag(self, library_id: LibraryId, patron_id: PatronId, flagged_at: datetime) -> None:
        namespace = _hardship_namespace(library_id, patron_id)
        fact = HardshipHistoryFact(flagged_at=flagged_at)
        self._client.create_event(
            memory_id=self._memory_id, actor_id=namespace, session_id=f"{library_id}:{patron_id}",
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
