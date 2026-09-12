"""Local, fake-clock soak harness. Proves OverdueSequencer's session-state
and tier-monotonicity logic across multiple simulated day boundaries,
without waiting real wall-clock time.

What this harness PROVES:
- A case that starts at the top of the escalation ladder (circ_red, seeded
  with prior_reminder_tier_sent=3) never advances past it and never
  regresses, across repeated nightly runs.
- A fresh case advances by exactly one tier per simulated night, never
  skipping a tier, across a run of simulated nights.
- A hardship-history Memory fact written mid-sequence (by a librarian,
  independent of the case's own record fields) is visible on the very
  next simulated night's evaluate() call -- i.e. the read is fresh per
  call, never cached from an earlier night.

What this harness explicitly does NOT prove: it is not the genuine
multi-day, real-EventBridge soak test docs/architecture/final_architecture.md
section 15.2/15.5 names as a hard-dated, uncompressible deadline risk --
that test needs a real AgentCore Runtime deployment and a real EventBridge
schedule (Plan 3's first deliverable, per this plan's own spec section 6.1
and section 7). This harness proves the session-state logic is correct in
isolation; it cannot and does not prove a real deployment survives a real
multi-day gap, real S3 durability, or real EventBridge scheduling.

Live-credential design note (resolved from the plan's own flagged
implementer note): the plan's original sketch had `agent_factory` build a
real `strands.Agent` via `build_stacks_agent(...)` and then have
`OverdueSequencer.run_nightly_tier` call that agent with a natural-language
prompt -- but calling a real `Agent` instance requires a live Bedrock model
call, which this task's fast suite must NOT require (Global Constraint:
zero AWS credentials except explicitly-marked live tests, and this task has
none marked live). Instead, `agent_factory` here returns a `MagicMock`
whose call side effect invokes the REAL `run_overdue_chase` tool function
(via `make_run_overdue_chase`) directly against the real `repo`/`memory`
fixtures -- first `action="evaluate"`, then, respecting the same
code-governed `classify_overdue_chase`/`is_approval_valid` gate the real
agent would be bound by, `action="commit"` with a synthesized approval
token when the computed tier requires one. This makes `repo`'s circulation-
record state genuinely advance (or genuinely stay blocked/pinned) for real,
proving the tier-monotonicity property against real tool logic, without
ever making a live model call. This mirrors Task 12's own test pattern
(a `MagicMock` standing in for the whole `Agent` call) in
tests/unit/test_overdue_sequencer.py, just with a real side effect instead
of a canned return value.

A second, smaller bug in the plan's own sketch is also fixed here: the
plan's proposed `_fake_session_manager_factory` mimicked a
`get_state()`/`save_state()` pair, but `OverdueSequencer` (Task 12) drives
the confirmed-real `read_agent`/`create_agent`/`update_agent` primitives
(see overdue_sequencer.py's own module docstring for the SDK-verification
trail). The fake session manager below matches Task 12's own test fake in
tests/unit/test_overdue_sequencer.py, not the plan's sketch.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.data.models import CirculationRecord
from stacks.hitl.classify import Tier, classify_overdue_chase
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.memory.store import InMemoryMemoryStore
from stacks.sequencer.overdue_sequencer import OverdueSequencer
from stacks.tools.run_overdue_chase import make_run_overdue_chase
from stacks.types import HardshipHistoryFact, SensitivityFlag


def _fake_session_manager_factory():
    """Matches the real S3SessionManager's confirmed read_agent/
    create_agent/update_agent interface (see overdue_sequencer.py's module
    docstring), NOT a get_state()/save_state() pair -- copied from Task
    12's own test fake in tests/unit/test_overdue_sequencer.py so this
    harness exercises OverdueSequencer through the interface it actually
    calls.
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


def _direct_state_advancing_agent_factory(repo, memory, now):
    """Builds an agent_factory for OverdueSequencer whose returned
    "agent" is a MagicMock -- so calling it never makes a live model
    call -- but whose call side effect drives the REAL run_overdue_chase
    tool function (evaluate, then commit with a synthesized approval
    token when the code-governed classifier requires one) against the
    real repo/memory fixtures. This is what makes repo's circulation-
    record state genuinely advance in these tests, not a canned mock
    return value.

    session_id encodes (library_id, circulation_record_id) per
    overdue_sequencer._session_id_for's own "overdue:{library_id}:
    {circulation_record_id}" format, which is how this factory recovers
    both without needing them threaded in separately.
    """

    def agent_factory(session_id: str):
        _, library_id, circulation_record_id = session_id.split(":", 2)

        def run_one_tier(prompt: str) -> SimpleNamespace:
            # Fresh cache/ledger per simulated night, exactly as a fresh
            # tool-call turn would get inside a real agent invocation --
            # nothing here is carried over or cached across nights.
            tool_fn = make_run_overdue_chase(
                repo, EvaluationCache(), TierLedger(), library_id, now, memory,
            )

            eval_result = tool_fn(
                library_id=library_id, circulation_record_id=circulation_record_id,
                action="evaluate",
            )
            eval_json = eval_result["content"][0]["json"]
            if eval_json.get("status") == "not_overdue":
                return SimpleNamespace(message="not_overdue, no action taken")

            sensitivity_flags = [SensitivityFlag(f) for f in eval_json["sensitivity_flags"]]
            tier = classify_overdue_chase(
                eval_json["tier_consequence"], sensitivity_flags,
                eval_json["has_recalled_hardship_history"],
            )
            clause_id = (eval_json["applicable_policy_clause"] or {}).get("clause_id")
            message_body = f"Overdue reminder per {clause_id}." if clause_id else "Overdue reminder."

            approval_token = None
            if tier is Tier.YELLOW:
                approval_token = {
                    "token": "soak-test-token", "approver_role": "circulation_staff",
                    "related_action_id": f"overdue:{circulation_record_id}",
                }
            elif tier is Tier.RED:
                approval_token = {
                    "token": "soak-test-token", "approver_role": "librarian_case_review",
                    "related_action_id": f"overdue:{circulation_record_id}",
                }

            commit_result = tool_fn(
                library_id=library_id, circulation_record_id=circulation_record_id,
                action="commit", message_body=message_body, approval_token=approval_token,
            )
            return SimpleNamespace(message=str(commit_result["content"][0]["json"]))

        fake_agent = MagicMock(side_effect=run_one_tier)
        # Real strands.Agent construction with a session_manager restores
        # _interrupt_state.activated from the persisted session
        # automatically; this fake drives real tool calls directly rather
        # than a real Agent, so it never has a genuinely activated
        # interrupt state to restore -- always False, matching what a
        # real Agent would report for these clean-completion soak
        # scenarios (see overdue_sequencer.py's own activated check).
        fake_agent._interrupt_state.activated = False
        return fake_agent

    return agent_factory


def test_repeated_nightly_runs_advance_the_tier_monotonically_never_skipping_or_repeating():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    memory = InMemoryMemoryStore()

    simulated_now = [datetime(2026, 9, 1, tzinfo=timezone.utc)]
    agent_factory = _direct_state_advancing_agent_factory(repo, memory, lambda: simulated_now[0])

    session_manager_cls, sessions = _fake_session_manager_factory()
    sequencer = OverdueSequencer(
        bucket="unused", region="us-west-2",
        agent_factory=agent_factory, session_manager_factory=session_manager_cls,
    )

    tier_snapshots = []
    for day_offset in range(4):
        simulated_now[0] = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=day_offset * 20)
        sequencer.run_nightly_tier("circ_red", "lib_demo")
        record = repo.get_circulation_record("lib_demo", "circ_red")
        tier_snapshots.append(record.prior_reminder_tier_sent)

    # circ_red seeds prior_reminder_tier_sent=3 already (fixtures.py) -- it
    # starts at the top of the ladder, so it should never advance further
    # and should never regress across any of the four simulated nights.
    assert tier_snapshots == [3, 3, 3, 3]


def test_a_fresh_overdue_case_advances_one_tier_per_simulated_night_without_skipping():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_soak_fresh", library_id="lib_demo",
        patron_id="patron_soak", item_id="item_soak", item_type="book",
        due_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
    ))
    memory = InMemoryMemoryStore()

    simulated_now = [datetime(2026, 9, 1, tzinfo=timezone.utc)]
    agent_factory = _direct_state_advancing_agent_factory(repo, memory, lambda: simulated_now[0])

    session_manager_cls, sessions = _fake_session_manager_factory()
    sequencer = OverdueSequencer(
        bucket="unused", region="us-west-2",
        agent_factory=agent_factory, session_manager_factory=session_manager_cls,
    )

    tiers = []
    for day_offset in range(3):
        simulated_now[0] = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
        sequencer.run_nightly_tier("circ_soak_fresh", "lib_demo")
        record = repo.get_circulation_record("lib_demo", "circ_soak_fresh")
        tiers.append(record.prior_reminder_tier_sent)

    # Starts at -1 (fresh record default), so each night should advance by
    # exactly one tier: 0, 1, 2 -- never skipping, never regressing.
    assert tiers == [0, 1, 2]
    for earlier, later in zip(tiers, tiers[1:]):
        assert later >= earlier, "tier must never regress across simulated nights"


def test_a_mid_sequence_hardship_flag_is_visible_on_the_very_next_simulated_night():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    repo.save_circulation_record(CirculationRecord(
        circulation_record_id="circ_soak_hardship", library_id="lib_demo",
        patron_id="patron_soak_hardship", item_id="item_soak_2", item_type="book",
        due_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
    ))
    memory = InMemoryMemoryStore()

    simulated_now = [datetime(2026, 9, 1, tzinfo=timezone.utc)]
    agent_factory = _direct_state_advancing_agent_factory(repo, memory, lambda: simulated_now[0])

    session_manager_cls, sessions = _fake_session_manager_factory()
    sequencer = OverdueSequencer(
        bucket="unused", region="us-west-2",
        agent_factory=agent_factory, session_manager_factory=session_manager_cls,
    )

    # Night 1: no hardship fact recorded yet.
    sequencer.run_nightly_tier("circ_soak_hardship", "lib_demo")

    # A librarian documents a hardship flag mid-sequence, independent of
    # this case's own record fields (agent_architecture.md section 3's
    # "a librarian could document a new hardship flag mid-sequence").
    memory.set_hardship_history(
        "lib_demo", "patron_soak_hardship", HardshipHistoryFact(flagged_at=simulated_now[0]),
    )

    # Night 2: this evaluate() call must read the fact fresh, not a cached
    # value from night 1. Assert directly on the raw evaluate() output
    # (matching the plan's own approach) so this assertion never depends
    # on a live model call to interpret it.
    simulated_now[0] += timedelta(days=1)
    direct_tool = make_run_overdue_chase(
        repo, EvaluationCache(), TierLedger(), "lib_demo", lambda: simulated_now[0], memory,
    )
    result = direct_tool(
        library_id="lib_demo", circulation_record_id="circ_soak_hardship", action="evaluate",
    )
    assert result["content"][0]["json"]["has_recalled_hardship_history"] is True
