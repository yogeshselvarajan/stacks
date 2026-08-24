"""Tests for OverdueSequencer -- session-per-case wrapper around
run_overdue_chase, driven by a FAKE session-manager factory so this
fast suite never touches real S3/AWS. See src/stacks/sequencer/
overdue_sequencer.py's own module docstring for why the fake below
mimics read_agent/create_agent/update_agent rather than the
get_state()/save_state() pair originally guessed in the plan: direct
introspection of the installed SDK found no such methods on the real
strands.session.s3_session_manager.S3SessionManager (or anywhere in its
MRO) -- the real, confirmed persistence primitives for arbitrary
app-defined per-case state are read_agent/create_agent/update_agent
against a strands.types.session.SessionAgent's state dict.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from stacks.sequencer.overdue_sequencer import OverdueSequencer


def _fake_session_manager_factory():
    """A stand-in for S3SessionManager during fast, no-AWS tests -- this
    task's own tests exercise OverdueSequencer's case-lookup and
    per-tier-invocation logic against a fake session store; Task 14's
    live test exercises the real S3SessionManager class end to end. This
    split mirrors every other Protocol/fake-vs-real split in this plan.

    Mimics the real S3SessionManager's confirmed read_agent/create_agent/
    update_agent methods (not get_state/save_state -- see this file's
    module docstring), keyed by session_id, holding one synthetic
    "agent" record's state dict per session.
    """
    sessions: dict[str, dict] = {}

    class FakeSessionManager:
        def __init__(self, session_id: str, **kwargs):
            self.session_id = session_id

        def read_agent(self, session_id: str, agent_id: str):
            state = sessions.get(session_id)
            if state is None:
                return None
            return SimpleNamespace(state=dict(state))

        def create_agent(self, session_id: str, session_agent):
            sessions[session_id] = dict(session_agent.state)

        def update_agent(self, session_id: str, session_agent):
            sessions[session_id] = dict(session_agent.state)

    return FakeSessionManager, sessions


def test_run_nightly_tier_invokes_the_agent_and_records_tier_history():
    session_manager_cls, sessions = _fake_session_manager_factory()
    agent = MagicMock()
    agent.return_value = MagicMock(message="Sent tier 0 reminder for circ_1, cited OD-1.")

    sequencer = OverdueSequencer(
        bucket="unused-in-this-test", region="us-west-2",
        agent_factory=lambda session_id: agent,
        session_manager_factory=session_manager_cls,
    )

    result = sequencer.run_nightly_tier("circ_1", "lib_demo")

    assert agent.called
    session_id = "overdue:lib_demo:circ_1"
    assert sessions[session_id]["tier_history"]
    assert result["session_id"] == session_id


def test_run_nightly_tier_reuses_the_same_session_across_two_nights():
    session_manager_cls, sessions = _fake_session_manager_factory()
    agent = MagicMock()
    agent.return_value = MagicMock(message="ok")

    sequencer = OverdueSequencer(
        bucket="unused-in-this-test", region="us-west-2",
        agent_factory=lambda session_id: agent,
        session_manager_factory=session_manager_cls,
    )

    sequencer.run_nightly_tier("circ_1", "lib_demo")
    sequencer.run_nightly_tier("circ_1", "lib_demo")

    session_id = "overdue:lib_demo:circ_1"
    assert len(sessions[session_id]["tier_history"]) == 2


def test_run_nightly_tier_records_pending_approval_on_interrupt():
    """Whole-branch review Important 5: run_nightly_tier previously
    recorded only str(getattr(result, "message", result)) into
    tier_history, discarding stop_reason and result.interrupts entirely.
    A YELLOW/RED-tier escalation reaching a HITL interrupt looked
    identical in tier_history to a cleanly completed run, with no visible
    signal that a human needs to act. Verifies stop_reason and
    interrupt_ids land in tier_history, and pending_approval lands in the
    return dict, when the agent returns an interrupted AgentResult."""
    session_manager_cls, sessions = _fake_session_manager_factory()

    fake_interrupt = SimpleNamespace(id="hitl:run_overdue_chase:circ_1")
    agent = MagicMock()
    agent.return_value = SimpleNamespace(
        message="Escalation for circ_1 is pending human approval.",
        stop_reason="interrupt",
        interrupts=[fake_interrupt],
    )

    sequencer = OverdueSequencer(
        bucket="unused-in-this-test", region="us-west-2",
        agent_factory=lambda session_id: agent,
        session_manager_factory=session_manager_cls,
    )

    result = sequencer.run_nightly_tier("circ_1", "lib_demo")

    assert result["pending_approval"] is True
    session_id = "overdue:lib_demo:circ_1"
    recorded = sessions[session_id]["tier_history"][-1]
    assert recorded["stop_reason"] == "interrupt"
    assert recorded["interrupt_ids"] == ["hitl:run_overdue_chase:circ_1"]


def test_run_nightly_tier_records_no_pending_approval_on_clean_completion():
    """The counterpart to the interrupt test above -- a normal completion
    (no stop_reason attribute, no interrupts) must not be mistaken for a
    pending-approval case."""
    session_manager_cls, sessions = _fake_session_manager_factory()
    agent = MagicMock()
    agent.return_value = MagicMock(message="ok")
    del agent.return_value.stop_reason  # ensure getattr falls back to None
    del agent.return_value.interrupts

    sequencer = OverdueSequencer(
        bucket="unused-in-this-test", region="us-west-2",
        agent_factory=lambda session_id: agent,
        session_manager_factory=session_manager_cls,
    )

    result = sequencer.run_nightly_tier("circ_1", "lib_demo")

    assert result["pending_approval"] is False
    session_id = "overdue:lib_demo:circ_1"
    recorded = sessions[session_id]["tier_history"][-1]
    assert recorded["stop_reason"] is None
    assert recorded["interrupt_ids"] == []


def test_session_id_is_library_scoped_so_two_libraries_never_collide():
    session_manager_cls, sessions = _fake_session_manager_factory()
    agent = MagicMock()
    agent.return_value = MagicMock(message="ok")

    sequencer = OverdueSequencer(
        bucket="unused-in-this-test", region="us-west-2",
        agent_factory=lambda session_id: agent,
        session_manager_factory=session_manager_cls,
    )

    sequencer.run_nightly_tier("circ_shared_id", "lib_a")
    sequencer.run_nightly_tier("circ_shared_id", "lib_b")

    assert "overdue:lib_a:circ_shared_id" in sessions
    assert "overdue:lib_b:circ_shared_id" in sessions
    assert len(sessions["overdue:lib_a:circ_shared_id"]["tier_history"]) == 1
    assert len(sessions["overdue:lib_b:circ_shared_id"]["tier_history"]) == 1
