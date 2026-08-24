import os
import time
from datetime import datetime, timezone

import pytest

from stacks.memory.agentcore_store import AgentCoreMemoryStore


def test_live_write_then_read_ill_substitution_pattern():
    memory_id = os.environ.get("STACKS_TEST_AGENTCORE_MEMORY_ID")
    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    if not memory_id:
        pytest.skip("STACKS_TEST_AGENTCORE_MEMORY_ID not set -- run scripts/provision_agentcore_memory.py first")

    store = AgentCoreMemoryStore(memory_id=memory_id, region=region)
    library_id = "lib_demo"
    requester_key = f"test_patron_{int(time.time())}"

    store.record_ill_routing_event(
        library_id, requester_key,
        request_frequency_delta=1, subject_area="history", resolved_via_substitution=True,
    )

    result = None
    for _ in range(12):
        result = store.get_ill_substitution_pattern(library_id, requester_key)
        if result is not None:
            break
        time.sleep(5)

    assert result is not None, (
        "Fact not visible via retrieve_memories after 60s of polling. "
        "Record the actual observed latency in this test's docstring or a "
        "code comment once run -- this is the empirical answer to the "
        "SDK-verification note's open question, not an assumption."
    )
    assert result.request_frequency >= 1
    assert result.has_accepted_substitution_without_escalation is True


def test_live_write_then_read_hardship_history():
    memory_id = os.environ.get("STACKS_TEST_AGENTCORE_MEMORY_ID")
    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    if not memory_id:
        pytest.skip("STACKS_TEST_AGENTCORE_MEMORY_ID not set -- run scripts/provision_agentcore_memory.py first")

    store = AgentCoreMemoryStore(memory_id=memory_id, region=region)
    library_id = "lib_demo"
    patron_id = f"test_patron_hardship_{int(time.time())}"

    store.record_hardship_flag(library_id, patron_id, flagged_at=datetime.now(timezone.utc))

    result = None
    for _ in range(12):
        result = store.get_hardship_history(library_id, patron_id)
        if result is not None:
            break
        time.sleep(5)

    assert result is not None
