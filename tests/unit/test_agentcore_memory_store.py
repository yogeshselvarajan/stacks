import os
import pathlib
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from stacks.memory.agentcore_store import AgentCoreMemoryStore, _hardship_namespace, _ill_namespace


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


def test_ill_namespace_actor_id_and_query_are_the_same_composite_string():
    """Whole-branch review Important 6 regression guard, offline and no
    AWS call needed: create_event's actor_id and retrieve_memories'
    namespace/actor_id/query must all be the exact same string for a
    given (library_id, requester_key), or a write can never be found by a
    later read regardless of what the provisioning script's
    namespace_templates resolve to."""
    fake_client = MagicMock()
    fake_client.retrieve_memories.return_value = []

    with patch("stacks.memory.agentcore_store.MemoryClient", return_value=fake_client):
        store = AgentCoreMemoryStore(memory_id="mem_1", region="us-west-2")
        store.get_ill_substitution_pattern("lib_demo", "patron_1")

    _, kwargs = fake_client.retrieve_memories.call_args
    assert kwargs["namespace"] == kwargs["actor_id"] == kwargs["query"] == "ill_pattern:lib_demo:patron_1"


def test_ill_record_writes_with_the_same_composite_string_as_actor_id():
    fake_client = MagicMock()
    fake_client.retrieve_memories.return_value = []  # existing = None, read-before-merge inside record_ill_routing_event

    with patch("stacks.memory.agentcore_store.MemoryClient", return_value=fake_client):
        store = AgentCoreMemoryStore(memory_id="mem_1", region="us-west-2")
        store.record_ill_routing_event(
            "lib_demo", "patron_1", request_frequency_delta=1, subject_area=None, resolved_via_substitution=False,
        )

    _, kwargs = fake_client.create_event.call_args
    assert kwargs["actor_id"] == "ill_pattern:lib_demo:patron_1"


def test_hardship_namespace_actor_id_and_query_are_the_same_composite_string():
    fake_client = MagicMock()
    fake_client.retrieve_memories.return_value = []

    with patch("stacks.memory.agentcore_store.MemoryClient", return_value=fake_client):
        store = AgentCoreMemoryStore(memory_id="mem_1", region="us-west-2")
        store.get_hardship_history("lib_demo", "patron_2")

    _, kwargs = fake_client.retrieve_memories.call_args
    assert kwargs["namespace"] == kwargs["actor_id"] == kwargs["query"] == "hardship:lib_demo:patron_2"


def test_hardship_record_writes_with_the_same_composite_string_as_actor_id():
    fake_client = MagicMock()

    with patch("stacks.memory.agentcore_store.MemoryClient", return_value=fake_client):
        store = AgentCoreMemoryStore(memory_id="mem_1", region="us-west-2")
        store.record_hardship_flag("lib_demo", "patron_2", flagged_at=datetime.now(timezone.utc))

    _, kwargs = fake_client.create_event.call_args
    assert kwargs["actor_id"] == "hardship:lib_demo:patron_2"


def test_ill_and_hardship_namespaces_for_the_same_library_and_key_never_collide():
    """The two workflows' composite namespaces must be disjoint even for
    the exact same library_id and entity key -- prefixed by workflow, so
    a patron who is also an ILL requester never has one workflow's fact
    read back for the other's namespace."""
    assert _ill_namespace("lib_demo", "same_id") != _hardship_namespace("lib_demo", "same_id")


def test_provisioning_script_namespace_templates_resolve_to_exactly_actor_id():
    """Static, no-AWS-call regression guard for the exact self-inconsistency
    this finding closed: both strategies' namespace_templates must be
    exactly ["{actorId}"] (the AgentCore Memory placeholder that resolves
    to precisely the create_event actor_id passed at write time, with no
    extra path segments), matching what this store passes as namespace
    when reading. Reads the provisioning script's own source rather than
    running it (Global Constraints: provisioning is never a side effect
    of running tests)."""
    script_path = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "provision_agentcore_memory.py"
    source = script_path.read_text()
    # >= 2 rather than == 2: the module docstring also mentions the exact
    # template string in prose, so the two real add_semantic_strategy_and_wait
    # call sites are a floor, not an exact count.
    assert source.count('namespace_templates=["{actorId}"]') >= 2
    assert "namespaces=[" not in source  # the deprecated kwarg must not have crept back in
