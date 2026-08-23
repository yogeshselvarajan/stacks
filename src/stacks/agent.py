"""Builds the Stacks Agent: registers the five Plan 1 tools and two hooks
(HITL gate, audit log) against a shared repository and HITL support
objects. See docs/architecture/final_architecture.md section 4.2.

Plan 1 scope: single agent, five tools (get_library_data,
resolve_room_conflict, route_ill_request, run_overdue_chase,
notify_parties). The sixth tool (disambiguate_ill_candidates, the ILL
Disambiguation Specialist wrapper) and AgentCore Memory/Identity wiring
are later plans -- see CLAUDE.md's build order.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Callable

from strands import Agent
from strands.models import BedrockModel

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.hitl_gate import HitlGateHook
from stacks.hitl.tier_ledger import TierLedger
from stacks.hooks.audit_log import AuditLogHook, AuditLogSink
from stacks.tools.get_library_data import make_get_library_data
from stacks.tools.notify_parties import NotificationSink, make_notify_parties
from stacks.tools.resolve_room_conflict import make_resolve_room_conflict
from stacks.tools.route_ill_request import make_route_ill_request
from stacks.tools.run_overdue_chase import make_run_overdue_chase

SYSTEM_PROMPT = """You are Stacks, an agent that helps library staff resolve \
room-booking conflicts, route ambiguous interlibrary-loan requests, and run \
overdue-item chasing.

For every case, call the relevant tool's evaluate action first, reason only \
over what that tool returns, then call commit with a rationale that cites \
the applicable policy clause's clause_id verbatim. Never invent a \
resolution, routing target, or policy clause that was not present in a \
tool's own response. If a commit is blocked pending human approval, say so \
plainly and stop; do not retry the same commit without a new approval_token. \
After a successful commit that a workflow requires notifying about, call \
notify_parties with related_action_id set to the commit result's own \
related_action_id field."""


class StacksAgentBundle:
    """Everything the integration test, and later a BFF caller, needs
    direct access to alongside the Agent itself."""

    def __init__(self, agent: Agent, audit_sink: AuditLogSink, notification_sink: NotificationSink) -> None:
        self.agent = agent
        self.audit_sink = audit_sink
        self.notification_sink = notification_sink


def build_stacks_agent(
    repo: LibraryDataRepository,
    library_id: str,
    session_id: str,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> StacksAgentBundle:
    """Builds one Stacks Agent scoped to one library tenant and one session.

    library_id is passed directly here at Plan 1 scope. A later plan
    (AgentCore Identity integration) replaces the caller of this function
    with one that reads library_id from a verified JWT claim instead of a
    plain argument; this function's own body does not change.
    """
    room_conflict_cache = EvaluationCache()
    ill_cache = EvaluationCache()
    overdue_cache = EvaluationCache()
    tier_ledger = TierLedger()
    audit_sink = AuditLogSink()
    notification_sink = NotificationSink()

    get_library_data = make_get_library_data(repo, library_id)
    resolve_room_conflict = make_resolve_room_conflict(repo, room_conflict_cache, tier_ledger, library_id)
    route_ill_request = make_route_ill_request(repo, ill_cache, tier_ledger, library_id)
    run_overdue_chase = make_run_overdue_chase(repo, overdue_cache, tier_ledger, library_id, now)
    notify_parties = make_notify_parties(repo, notification_sink, tier_ledger, library_id)

    hitl_gate = HitlGateHook(room_conflict_cache, ill_cache, overdue_cache)
    audit_log = AuditLogHook(audit_sink, session_id, library_id)

    model = BedrockModel(
        model_id=os.environ.get("STACKS_BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"),
        region_name=os.environ.get("STACKS_AWS_REGION", "us-west-2"),
        temperature=0.2,
    )

    agent = Agent(
        model=model,
        tools=[get_library_data, resolve_room_conflict, route_ill_request, run_overdue_chase, notify_parties],
        hooks=[hitl_gate, audit_log],
        system_prompt=SYSTEM_PROMPT,
    )

    return StacksAgentBundle(agent, audit_sink, notification_sink)
