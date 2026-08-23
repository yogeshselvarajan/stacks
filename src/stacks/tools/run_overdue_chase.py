"""run_overdue_chase -- evaluate/commit for context-aware overdue-item
chasing. Plan 1 scope: no AgentCore Memory (has_recalled_hardship_history
always False) and executed as a plain tool call, not yet driven by the
Overdue Escalation Sequencer's Session Management + EventBridge nightly
schedule. See docs/architecture/tool_architecture.md section 3.4.
"""
from __future__ import annotations

from typing import Any, Callable

from strands import tool

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Workflow, classify_overdue_chase, is_approval_valid
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.types import ApprovalToken, SensitivityFlag

_ESCALATION_LADDER = ["informational", "fee_mention", "hold_block", "collections_referral"]


def make_run_overdue_chase(
    repo: LibraryDataRepository,
    cache: EvaluationCache,
    tier_ledger: TierLedger,
    session_library_id: str,
    now: Callable[[], Any],
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
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "not_overdue", "escalation_log_write": None, "overdue_session_step_id": None}}]}

        days_overdue = (now() - record.due_date).days
        if days_overdue <= 0:
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "not_overdue", "escalation_log_write": None, "overdue_session_step_id": None}}]}

        next_tier_index = min(record.prior_reminder_tier_sent + 1, len(_ESCALATION_LADDER) - 1) if record.prior_reminder_tier_sent > 0 else 0
        tier_consequence = _ESCALATION_LADDER[next_tier_index]

        if action == "evaluate":
            clauses = repo.get_policy_clauses(library_id, "overdue_escalation")
            clause = clauses[0].model_dump(mode="json") if clauses else None
            evaluation = {
                "circulation_record_id": circulation_record_id,
                "days_overdue": days_overdue,
                "prior_reminder_tier_sent": record.prior_reminder_tier_sent,
                "recommended_next_tier": next_tier_index,
                "applicable_policy_clause": clause,
                "sensitivity_flags": [f.value for f in record.flags],
                "tier_consequence": tier_consequence,
                "has_recalled_hardship_history": False,
            }
            cache.put(library_id, circulation_record_id, evaluation)
            return {"status": "success", "content": [{"json": evaluation}]}

        if action == "commit":
            evaluation = cache.get(library_id, circulation_record_id)
            if evaluation is None:
                return {"status": "error", "content": [{"text": "evaluate_not_called"}]}

            sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
            tier = classify_overdue_chase(evaluation["tier_consequence"], sensitivity_flags, evaluation["has_recalled_hardship_history"])
            token = ApprovalToken(**approval_token) if approval_token else None
            if not is_approval_valid(tier, token.approver_role if token else None, Workflow.OVERDUE_CHASE):
                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None}}]}

            clause_id = (evaluation["applicable_policy_clause"] or {}).get("clause_id")
            if clause_id and (not message_body or clause_id not in message_body):
                return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "blocked_missing_approval", "escalation_log_write": None, "overdue_session_step_id": None}}]}

            record.prior_reminder_tier_sent = evaluation["recommended_next_tier"]
            repo.save_circulation_record(record)
            related_action_id = f"overdue:{circulation_record_id}"
            tier_ledger.record(library_id, related_action_id, tier, Workflow.OVERDUE_CHASE)
            escalation_log_write = {"circulation_record_id": circulation_record_id, "tier_sent": evaluation["recommended_next_tier"], "related_action_id": related_action_id}
            return {"status": "success", "content": [{"json": {"circulation_record_id": circulation_record_id, "status": "committed", "escalation_log_write": escalation_log_write, "overdue_session_step_id": None}}]}

        return {"status": "error", "content": [{"text": f"invalid_action: {action!r}"}]}

    return run_overdue_chase
