"""run_overdue_chase -- evaluate/commit for context-aware overdue-item
chasing. Plan 1 scope: no AgentCore Memory (has_recalled_hardship_history
always False) and executed as a plain tool call, not yet driven by the
Overdue Escalation Sequencer's Session Management + EventBridge nightly
schedule. Unlike the three single-shot tools (resolve_room_conflict,
route_ill_request, notify_parties), this tool is expected to be invoked
repeatedly over time for the same circulation record with prior_reminder_tier_sent
advancing monotonically by one tier per cycle. See docs/architecture/
tool_architecture.md section 3.4.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from strands import tool

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Workflow, classify_overdue_chase, is_approval_valid
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.memory.store import MemoryStore
from stacks.types import ApprovalToken, SensitivityFlag

_ESCALATION_LADDER = ["informational", "fee_mention", "hold_block", "collections_referral"]

_SEVERITY_SIGNALS = {
    1: ("fee", "fine", "charge"),
    2: ("hold", "blocked", "suspended", "restricted"),
    3: ("collections", "collection agency", "legal action", "referred to collections"),
}

_HARDSHIP_RECENCY_WINDOW_DAYS = 365  # agent_architecture.md section 4.4's example figure, per this plan's spec section 4.2


def make_run_overdue_chase(
    repo: LibraryDataRepository,
    cache: EvaluationCache,
    tier_ledger: TierLedger,
    session_library_id: str,
    now: Callable[[], Any],
    memory: MemoryStore,
):
    @tool
    def run_overdue_chase(
        library_id: str,
        circulation_record_id: str,
        action: str,
        message_body: str | None = None,
        approval_token: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate or commit the next overdue-reminder tier for a
        circulation record.

        Args:
            library_id: Tenant scope; must match the session's own library_id.
            circulation_record_id: The circulation record being chased.
            action: "evaluate" or "commit".
            message_body: commit-only. LLM-composed; must cite the evaluate
                response's clause_id.
            approval_token: commit-only for YELLOW/RED-classified cases.

        Returns:
            An evaluate result (days_overdue, recommended_next_tier,
            tier_consequence) or a commit result (status, escalation_log_write).
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        record = repo.get_circulation_record(library_id, circulation_record_id)
        if record is None:
            return {"status": "error", "content": [{"text": "not_found"}]}
        if record.returned:
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "not_overdue", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": None, "hitl_tier": None}}]}

        days_overdue = (now() - record.due_date).days
        if days_overdue <= 0:
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "not_overdue", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": None, "hitl_tier": None}}]}

        next_tier_index = min(record.prior_reminder_tier_sent + 1, len(_ESCALATION_LADDER) - 1)
        tier_consequence = _ESCALATION_LADDER[next_tier_index]

        def _compute_evaluation() -> dict[str, Any]:
            clauses = repo.get_policy_clauses(library_id, "overdue_escalation")
            clause = clauses[0].model_dump(mode="json") if clauses else None

            try:
                fact = memory.get_hardship_history(library_id, record.patron_id)
                has_recalled_hardship_history = fact is not None and (now() - fact.flagged_at).days <= _HARDSHIP_RECENCY_WINDOW_DAYS
            except Exception:
                has_recalled_hardship_history = True  # fail-closed: treated as equivalent to a live flag

            return {
                "circulation_record_id": circulation_record_id,
                "days_overdue": days_overdue,
                "prior_reminder_tier_sent": record.prior_reminder_tier_sent,
                "recommended_next_tier": next_tier_index,
                "applicable_policy_clause": clause,
                "sensitivity_flags": [f.value for f in record.flags],
                "tier_consequence": tier_consequence,
                "has_recalled_hardship_history": has_recalled_hardship_history,
                "patron_id": record.patron_id,
            }

        if action == "evaluate":
            evaluation = _compute_evaluation()
            cache.put(library_id, circulation_record_id, evaluation)
            return {"status": "success", "content": [{"json": evaluation}]}

        if action == "commit":
            evaluation = cache.get(library_id, circulation_record_id)
            if evaluation is None:
                # See resolve_room_conflict.py's identical comment: only a
                # resume (or an already-valid prior token) ever carries
                # approval_token, since HitlGateHook always sets one on a
                # successful resume before the tool ever runs. A commit
                # with no approval_token and no cached evaluate is still
                # exactly the case this check exists to catch: the model
                # skipped evaluate entirely in a single, same-process
                # turn. When a token is present, recomputing is exactly
                # equivalent to what a fresh evaluate call would return
                # right now -- the only values it depends on
                # (record.prior_reminder_tier_sent, the current policy
                # clause, current hardship history) are unchanged between
                # the two processes for a genuine resume, since nothing
                # writes prior_reminder_tier_sent until commit itself
                # runs, below.
                if approval_token is None:
                    return {"status": "error", "content": [{"text": "evaluate_not_called"}]}
                evaluation = _compute_evaluation()

            sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
            tier = classify_overdue_chase(evaluation["tier_consequence"], sensitivity_flags, evaluation["has_recalled_hardship_history"])

            # Compute related_action_id before approval check
            related_action_id = f"overdue:{circulation_record_id}"

            # Idempotency guard against this exact tier advance being
            # re-committed a second time. Unlike resolve_room_conflict and
            # route_ill_request (single-shot commits), run_overdue_chase is
            # invoked repeatedly over time for the same circulation record,
            # so related_action_id alone (constant across every night) is
            # not a safe idempotency key -- keying on it directly would
            # block every legitimate later night's escalation too. Instead
            # key on the specific tier this call would advance to
            # (evaluation["recommended_next_tier"], fixed at evaluate
            # time), so only a genuine re-commit of the SAME tier step is
            # blocked, never the next night's advance to a new tier.
            #
            # This closes a real double-escalation path: MemoryEventHook's
            # AfterToolCallEvent fires after this tool has already
            # mutated the repository and tier_ledger, so if it then
            # rewrites event.result to an error (its fail-closed
            # behavior), a caller that retries after seeing that error
            # would otherwise re-evaluate at prior_reminder_tier_sent + 1
            # again -- advancing straight to the NEXT tier and skipping
            # this one, violating OD-1's "one tier per contact, never
            # skipping a tier" (whole-branch review Important 4).
            tier_advance_key = f"overdue_tier_advance:{circulation_record_id}:{evaluation['recommended_next_tier']}"
            if tier_ledger.get(library_id, tier_advance_key) is not None:
                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "already_committed", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": None}}]}

            # Parse and validate approval token (with fallback for malformed)
            token = None
            if approval_token:
                try:
                    token = ApprovalToken(**approval_token)
                    # Validate token's related_action_id matches computed one
                    if token.related_action_id != related_action_id:
                        return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": None}}]}
                except Exception:
                    # Malformed token: treat as no token supplied
                    token = None

            if not is_approval_valid(tier, token.approver_role if token else None, Workflow.OVERDUE_CHASE):
                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": None}}]}

            clause_id = (evaluation["applicable_policy_clause"] or {}).get("clause_id")
            if clause_id and (not message_body or clause_id not in message_body):
                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": None}}]}

            # Check message body doesn't contain severity keywords higher than recommended tier
            recommended_tier_index = evaluation["recommended_next_tier"]
            if message_body:
                message_lower = message_body.lower()
                for tier_index in range(recommended_tier_index + 1, len(_ESCALATION_LADDER)):
                    if tier_index in _SEVERITY_SIGNALS:
                        for keyword in _SEVERITY_SIGNALS[tier_index]:
                            if re.search(r"\b" + re.escape(keyword) + r"\b", message_lower):
                                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": None}}]}

            record.prior_reminder_tier_sent = max(record.prior_reminder_tier_sent, evaluation["recommended_next_tier"])
            repo.save_circulation_record(record)
            tier_ledger.record(library_id, related_action_id, tier, Workflow.OVERDUE_CHASE)
            tier_ledger.record(library_id, tier_advance_key, tier, Workflow.OVERDUE_CHASE)
            escalation_log_write = {"circulation_record_id": circulation_record_id, "tier_sent": evaluation["recommended_next_tier"], "related_action_id": related_action_id}
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "committed", "escalation_log_write": escalation_log_write, "overdue_session_step_id": None, "patron_id": evaluation["patron_id"], "hitl_tier": tier.value, "sensitivity_flags": evaluation["sensitivity_flags"]}}]}

        return {"status": "error", "content": [{"text": f"invalid_action: {action!r}"}]}

    return run_overdue_chase
