"""One-time setup: creates the Stacks AgentCore Memory resource and its
two named strategies, per docs/architecture/agent_architecture.md section
4.4. Run manually:

    python scripts/provision_agentcore_memory.py

Never imported by test code (Global Constraints).

NAMESPACE CONVENTION (whole-branch review Important 6, fixed 2026-08-24):
this script previously configured namespace_templates as
"/ill_pattern/{actorId}" and "/hardship/{actorId}" via the deprecated
`namespaces=` kwarg, while src/stacks/memory/agentcore_store.py queried
retrieve_memories with a plain "{library_id}:{requester_key}" namespace
and a separately workflow-prefixed actor_id -- resolving this script's
old template against that actor_id could never equal the namespace string
the store queried with (a self-inconsistency checkable by reading both
files, no AWS call needed). Both files now agree: the store computes one
composite string, f"{workflow_prefix}:{library_id}:{entity_key}", and
passes it unchanged as namespace, actor_id, and query alike (see
agentcore_store.py's own NAMESPACE CONVENTION note for the full rationale
and _ill_namespace/_hardship_namespace helpers). Each strategy below is
configured with namespace_templates=["{actorId}"] -- the AgentCore Memory
template placeholder that resolves to exactly the create_event actor_id
passed at write time, with no additional path segments -- since the
workflow prefix already lives inside the actor_id string itself, so the
two strategies do not need differently-shaped templates to stay disjoint.
This also switches from the deprecated `namespaces=` kwarg to
`namespace_templates=` (confirmed via
`inspect.getdoc(MemoryClient.add_semantic_strategy)`: the former is
documented "DEPRECATED. Use ``namespace_templates`` instead.").
"""
from __future__ import annotations

import os

from bedrock_agentcore.memory import MemoryClient

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")


def main() -> None:
    client = MemoryClient(region_name=REGION)

    result = client.create_memory_and_wait(
        name="stacks-library-memory",
        strategies=[],
        description="Stacks: ILL substitution pattern and overdue hardship-flag history",
        event_expiry_days=365,
    )
    memory_id = result["id"]
    print(f"Created memory: {memory_id}")

    client.add_semantic_strategy_and_wait(
        memory_id=memory_id, name="ill_substitution_pattern",
        description="Repeat ILL requester substitution-acceptance pattern",
        namespace_templates=["{actorId}"],
    )
    print("Added strategy: ill_substitution_pattern")

    client.add_semantic_strategy_and_wait(
        memory_id=memory_id, name="patron_hardship_history",
        description="Patron hardship-flag history from prior overdue cycles",
        namespace_templates=["{actorId}"],
    )
    print("Added strategy: patron_hardship_history")

    print()
    print("Set before running the live tests:")
    print(f"  STACKS_TEST_AGENTCORE_MEMORY_ID={memory_id}")


if __name__ == "__main__":
    main()
