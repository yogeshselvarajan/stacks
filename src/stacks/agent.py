"""Builds the Stacks Agent: registers the six tools and three hooks (HITL
gate, audit log, memory event) against a shared repository and HITL
support objects. See docs/architecture/final_architecture.md section 4.2.

Plan 1 scope was single agent, five tools (get_library_data,
resolve_room_conflict, route_ill_request, run_overdue_chase,
notify_parties). Plan 2 Task 8 wired a MemoryStore (defaulting to
InMemoryMemoryStore) and MemoryEventHook alongside the two Plan 1 hooks.
Plan 2 Task 11 wires in the sixth tool, disambiguate_ill_candidates (the
ILL Disambiguation Specialist wrapper, Agents-as-Tools). AgentCore
Identity and a real AgentCoreMemoryStore backing are still later plans --
see CLAUDE.md's build order.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Callable

from strands import Agent
from strands.models import BedrockModel
from strands.session.session_manager import SessionManager

from stacks.data.repository import LibraryDataRepository
from stacks.identity.claims import StaffIdentityClaims
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.hitl_gate import HitlGateHook
from stacks.hitl.pending_approvals import PendingApprovalsSink
from stacks.hitl.tier_ledger import TierLedger
from stacks.hooks.audit_log import AuditLogHook, AuditLogSink
from stacks.hooks.memory_event import MemoryEventHook
from stacks.memory.store import InMemoryMemoryStore, MemoryStore
from stacks.tools.disambiguate_ill_candidates import make_disambiguate_ill_candidates
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
the applicable policy clause's clause_id verbatim. The commit call is a \
separate tool call from the evaluate call and must repeat every one of that \
same case's identifying parameters in full -- conflicting_booking_ids for \
resolve_room_conflict, ill_request_id for route_ill_request, \
circulation_record_id for run_overdue_chase, and library_id for all three \
-- exactly as given to evaluate. Never omit them on the commit call just \
because you already computed them earlier in this turn. Never invent a \
resolution, routing target, or policy clause that was not present in a \
tool's own response. If a commit is blocked pending human approval, say so \
plainly and stop; do not retry the same commit without a new approval_token. \
After a successful commit that a workflow requires notifying about, call \
notify_parties with related_action_id set to the commit result's own \
related_action_id field. When route_ill_request's evaluate reports \
ambiguity 'multiple_editions', call disambiguate_ill_candidates with that \
evaluate response's own candidate_matches and requester_pattern before \
choosing a commit action; if it returns a confident narrowed_candidate_id, \
commit with that holding id and resolved_via_substitution=true; otherwise \
commit reflects the case is still ambiguous exactly as it already would \
without the specialist."""


class StacksAgentBundle:
    """Everything the integration test, and later a BFF caller, needs
    direct access to alongside the Agent itself."""

    def __init__(self, agent: Agent, audit_sink: AuditLogSink, notification_sink: NotificationSink) -> None:
        self.agent = agent
        self.audit_sink = audit_sink
        self.notification_sink = notification_sink


def build_stacks_agent(
    repo: LibraryDataRepository,
    claims: StaffIdentityClaims,
    session_id: str,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    memory: MemoryStore | None = None,
    pending_approvals_sink: PendingApprovalsSink | None = None,
    session_manager: SessionManager | None = None,
) -> StacksAgentBundle:
    """Builds one Stacks Agent scoped to one library tenant and one session.

    claims is a StaffIdentityClaims already verified by a ClaimsVerifier
    (stacks.identity.claims) -- library_id is read from it, never accepted
    as a bare, trusted string. docs/architecture/final_architecture.md
    section 10.4 step 3: the BFF constructs Invocation State from verified
    claims, never a client-supplied field.

    memory defaults to InMemoryMemoryStore() so every existing caller that
    doesn't pass one keeps working unchanged -- production/live-test
    callers pass a real AgentCoreMemoryStore explicitly.

    pending_approvals_sink and session_manager both default to None so
    every existing caller (Plan 1/2's ILL Specialist and Overdue Sequencer
    wiring, this module's own tests) keeps working unmodified. Without
    session_manager wired, a fresh Agent instance in a fresh process (the
    normal case on every AgentCore Runtime invocation) has no way to
    resume a paused interrupt from a prior invocation -- Task 5's main.py
    is the first real caller to pass both.
    """
    library_id = claims.library_id
    memory = memory if memory is not None else InMemoryMemoryStore()
    room_conflict_cache = EvaluationCache()
    ill_cache = EvaluationCache()
    overdue_cache = EvaluationCache()
    # The ILL Disambiguation Specialist's own convergence-result cache,
    # written by disambiguate_ill_candidates and read by both
    # route_ill_request's commit path and HitlGateHook -- shared the same
    # way the three EvaluationCache instances above are shared, so a
    # resolved_via_substitution claim can only take effect when the
    # specialist actually ran (whole-branch review Critical 1).
    ill_disambiguation_cache = EvaluationCache()
    tier_ledger = TierLedger()
    audit_sink = AuditLogSink()
    notification_sink = NotificationSink()

    get_library_data = make_get_library_data(repo, library_id)
    resolve_room_conflict = make_resolve_room_conflict(repo, room_conflict_cache, tier_ledger, library_id)
    route_ill_request = make_route_ill_request(repo, ill_cache, tier_ledger, library_id, memory, ill_disambiguation_cache)
    run_overdue_chase = make_run_overdue_chase(repo, overdue_cache, tier_ledger, library_id, now, memory)
    guardrail_client = None
    guardrail_id = os.environ.get("STACKS_BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.environ.get("STACKS_BEDROCK_GUARDRAIL_VERSION")
    if guardrail_id and guardrail_version:
        # Real Bedrock Guardrail (see scripts/provision_bedrock_guardrail.py).
        # Not set -> notify_parties falls back to its own denylist stand-in
        # (fail-open on missing config, not fail-closed, since a missing
        # Guardrail resource is an environment setup gap, not a signal that
        # notifications are unsafe -- the denylist is a strict subset of
        # what the real Guardrail also blocks).
        from stacks.guardrails.bedrock_guardrail import BedrockGuardrailClient

        guardrail_client = BedrockGuardrailClient(
            guardrail_id=guardrail_id, guardrail_version=guardrail_version,
            region=os.environ.get("STACKS_AWS_REGION", "us-west-2"),
        )
    notify_parties = make_notify_parties(repo, notification_sink, tier_ledger, library_id, guardrail_client=guardrail_client)

    hitl_gate = HitlGateHook(
        room_conflict_cache, ill_cache, overdue_cache, ill_disambiguation_cache,
        pending_approvals_sink=pending_approvals_sink, now=now, session_id=session_id,
    )
    audit_log = AuditLogHook(audit_sink, session_id, library_id, tier_ledger=tier_ledger)
    memory_event = MemoryEventHook(memory, library_id)

    model_id = os.environ.get("STACKS_BEDROCK_MODEL_ID")
    if not model_id:
        raise RuntimeError(
            "STACKS_BEDROCK_MODEL_ID environment variable must be set to a real "
            "Bedrock model ID (e.g. an inference profile ID with a date/version "
            "suffix). Per docs/architecture/final_architecture.md section 4.2, "
            "the model ID is never hardcoded -- there is deliberately no guessed "
            "fallback here, since a wrong guess fails at Bedrock invocation time "
            "with a confusing ValidationException rather than at startup."
        )

    model = BedrockModel(
        model_id=model_id,
        region_name=os.environ.get("STACKS_AWS_REGION", "us-west-2"),
        temperature=0.2,
    )

    disambiguate_ill_candidates = make_disambiguate_ill_candidates(repo, library_id, model, ill_disambiguation_cache)

    agent = Agent(
        model=model,
        tools=[
            get_library_data,
            resolve_room_conflict,
            route_ill_request,
            run_overdue_chase,
            notify_parties,
            disambiguate_ill_candidates,
        ],
        # Order matters here beyond readability: AfterToolCallEvent's
        # callbacks run in REVERSE registration order (confirmed via
        # strands.hooks.registry.AfterToolCallEvent.should_reverse_callbacks
        # == True), so memory_event's fail-closed error-rewrite (if the
        # Memory write fails) runs BEFORE audit_log sees event.result --
        # this is why a memory-write failure still gets correctly audited
        # as an error today. Do not reorder this list without preserving
        # that (whole-branch review Important 4).
        hooks=[hitl_gate, audit_log, memory_event],
        system_prompt=SYSTEM_PROMPT,
        session_manager=session_manager,
    )

    return StacksAgentBundle(agent, audit_sink, notification_sink)
