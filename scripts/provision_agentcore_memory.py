"""One-time setup: creates the Stacks AgentCore Memory resource and its
two named strategies, per docs/architecture/agent_architecture.md section
4.4. Run manually:

    python scripts/provision_agentcore_memory.py

Never imported by test code (Global Constraints).
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
        namespaces=["/ill_pattern/{actorId}"],
    )
    print("Added strategy: ill_substitution_pattern")

    client.add_semantic_strategy_and_wait(
        memory_id=memory_id, name="patron_hardship_history",
        description="Patron hardship-flag history from prior overdue cycles",
        namespaces=["/hardship/{actorId}"],
    )
    print("Added strategy: patron_hardship_history")

    print()
    print("Set before running the live tests:")
    print(f"  STACKS_TEST_AGENTCORE_MEMORY_ID={memory_id}")


if __name__ == "__main__":
    main()
