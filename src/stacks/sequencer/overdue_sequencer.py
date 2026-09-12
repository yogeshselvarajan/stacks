"""Overdue Escalation Sequencer -- session-state + nightly-schedule
durability wrapper around run_overdue_chase's existing reasoning. See
docs/architecture/agent_architecture.md section 3. Not a new agent
persona -- see this file's own design note in the plan task that created
it.

SDK-verification note (Task 12, 2026-08-24): S3SessionManager's
constructor signature (session_id, bucket, prefix, boto_session,
region_name) was confirmed correct via direct SDK introspection, but
this plan's original guess that its state read/write interface was a
simple get_state()/save_state() dict pair was WRONG -- no such methods
exist anywhere in its MRO (S3SessionManager -> RepositorySessionManager
-> SessionManager -> HookProvider -> SessionRepository -> ABC). Verified
with:

    python -c "from strands.session.s3_session_manager import \
S3SessionManager; print([m for m in dir(S3SessionManager) if not \
m.startswith('_')])"

which returned (among lifecycle methods for a real strands.Agent):
append_bidi_message, append_message, create_agent, create_message,
create_multi_agent, create_session, delete_session, initialize,
initialize_bidi_agent, initialize_multi_agent, list_messages, read_agent,
read_message, read_multi_agent, read_session, redact_latest_message,
register_hooks, sync_agent, sync_bidi_agent, sync_multi_agent,
update_agent, update_message, update_multi_agent.

The real class is a full Strands SessionManager + SessionRepository: it
persists an Agent's *conversation messages* and per-agent *user-managed
state* (a dict on strands.types.session.SessionAgent.state, populated
from agent.state.get()) via read_agent/create_agent/update_agent,
normally driven automatically by hooks when a real strands.Agent is
constructed with session_manager=session_manager. Because
OverdueSequencer's caller-supplied agent_factory only takes a session_id
(per this plan's fixed interface, consumed by Task 13/14) -- not this
session_manager instance -- and may return a plain callable/mock rather
than a session-wired Agent, this sequencer does not rely on that
automatic hook wiring. Instead it drives the confirmed-real
read_agent/create_agent/update_agent primitives directly against a
fixed, synthetic agent_id, storing tier_history in the resulting
SessionAgent's state dict. This is a deliberate, verified adaptation of
the plan's original get_state()/save_state() sketch, not a guess.

session_manager_factory defaults to strands.session.s3_session_manager.
S3SessionManager. Tests inject a fake factory (see
tests/unit/test_overdue_sequencer.py) so the fast suite never touches
S3; Task 14's live test uses the real default.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from strands.session.s3_session_manager import S3SessionManager
from strands.types.session import SessionAgent

# Fixed, synthetic agent_id under which OverdueSequencer stores its own
# tier_history via the session manager's SessionAgent.state -- this is
# not the id of any real strands.Agent; it is purely a storage key for
# this sequencer's own per-case bookkeeping inside the case's session.
_SEQUENCER_AGENT_ID = "overdue_sequencer"


def _session_id_for(library_id: str, circulation_record_id: str) -> str:
    return f"overdue:{library_id}:{circulation_record_id}"


class OverdueSequencer:
    """Session-per-case wrapper around run_overdue_chase. One nightly
    invocation of run_nightly_tier for a given (library_id,
    circulation_record_id) loads that case's durable session state,
    invokes one tier's worth of overdue-chasing reasoning via a caller
    constructed Agent, records the outcome, and saves the session --
    so a second night's invocation for the same case picks up where the
    first left off, and two libraries sharing a circulation_record_id
    never collide (the session_id is library-scoped).
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        agent_factory: Callable[[str], Any],
        session_manager_factory: Callable[..., Any] = S3SessionManager,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._agent_factory = agent_factory
        self._session_manager_factory = session_manager_factory

    def run_nightly_tier(self, circulation_record_id: str, library_id: str) -> dict[str, Any]:
        """Loads or creates this case's session, invokes one tier's worth
        of overdue-chasing reasoning via a session-bound Agent, saves the
        session, and returns the tier outcome.

        The hardship-history Memory read happens fresh on this call (via
        run_overdue_chase's own evaluate implementation, wired in Task 8)
        -- never cached from a prior night's invocation, per
        agent_architecture.md section 3's Memory requirements.
        """
        session_id = _session_id_for(library_id, circulation_record_id)
        session_manager = self._session_manager_factory(
            session_id=session_id, bucket=self._bucket, region_name=self._region,
        )

        existing = session_manager.read_agent(session_id, _SEQUENCER_AGENT_ID)
        tier_history = list(existing.state.get("tier_history", [])) if existing is not None else []

        agent = self._agent_factory(session_id)

        # A prior night's tier already raised a YELLOW/RED interrupt that
        # no human has resolved yet. Constructing this session-bound Agent
        # restores agent._interrupt_state.activated=True from the
        # persisted session (the same real session-restore mechanism a
        # BFF-resumed chat invocation relies on), and Strands requires the
        # very next agent(...) call to carry a list of interruptResponse
        # content while activated -- never a fresh plain-string prompt.
        # Calling agent(prompt) here with this sequencer's own plain
        # string prompt raised TypeError every single night until a human
        # approved/declined the case via the BFF's Approval Inbox (which
        # resumes the session properly and clears activated) -- confirmed
        # via real CloudWatch logs showing exactly this crash on 3
        # consecutive nights once a case's interrupt went unresolved.
        # There is nothing new for this sequencer to do until a human
        # acts, so skip invoking the agent entirely rather than crash.
        if agent._interrupt_state.activated:
            return {
                "circulation_record_id": circulation_record_id,
                "library_id": library_id,
                "session_id": session_id,
                "tier_history_length": len(tier_history),
                "pending_approval": True,
            }

        prompt = (
            f"Run the next overdue-chasing tier for circulation_record_id={circulation_record_id!r}, "
            f"library_id={library_id!r}. Call run_overdue_chase's evaluate action first, then commit "
            f"if appropriate, per your existing system prompt's rules."
        )
        result = agent(prompt)

        # A YELLOW/RED-tier escalation returns an AgentResult with
        # stop_reason == "interrupt" and populated result.interrupts,
        # rather than completing the commit. Recording only the
        # stringified message (as this file previously did) made a case
        # genuinely pending human approval look identical in tier_history
        # to one that completed cleanly -- so the next night's invocation
        # would silently re-attempt the same tier with no visible signal
        # that a human needs to act first (whole-branch review Important
        # 5). This does not build the full resume path (a later plan's
        # scope) -- it only makes the pending state observable.
        stop_reason = getattr(result, "stop_reason", None)
        interrupts = getattr(result, "interrupts", None) or []
        interrupt_ids = [getattr(i, "id", i) for i in interrupts]
        pending_approval = stop_reason == "interrupt"

        tier_history.append({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "agent_message": str(getattr(result, "message", result)),
            "stop_reason": stop_reason,
            "interrupt_ids": interrupt_ids,
        })

        session_agent = SessionAgent(
            agent_id=_SEQUENCER_AGENT_ID,
            state={"tier_history": tier_history},
            conversation_manager_state={},
        )
        if existing is None:
            session_manager.create_agent(session_id, session_agent)
        else:
            session_manager.update_agent(session_id, session_agent)

        return {
            "circulation_record_id": circulation_record_id,
            "library_id": library_id,
            "session_id": session_id,
            "tier_history_length": len(tier_history),
            "pending_approval": pending_approval,
        }
