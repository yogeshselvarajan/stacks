"""route_ill_request -- evaluate/commit for ambiguous ILL routing. Plan 1
scope: no AgentCore Memory (requester_pattern always None) and no ILL
Disambiguation Specialist (ambiguity="multiple_editions" stays YELLOW,
never auto-resolved by specialist convergence). See
docs/architecture/tool_architecture.md section 3.3.
"""
from __future__ import annotations

from typing import Any

from strands import tool

from stacks.data.models import ILLRequestStatus
from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Workflow, classify_ill_routing, is_approval_valid
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.types import ApprovalToken, SensitivityFlag


def make_route_ill_request(
    repo: LibraryDataRepository,
    cache: EvaluationCache,
    tier_ledger: TierLedger,
    session_library_id: str,
):
    @tool
    def route_ill_request(
        library_id: str,
        ill_request_id: str,
        action: str,
        chosen_holding_id: str | None = None,
        rationale: str | None = None,
        approval_token: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate or commit a routing decision for an interlibrary-loan
        request.

        Args:
            library_id: Tenant scope; must match the session's own library_id.
            ill_request_id: The ILL request being routed.
            action: "evaluate" or "commit".
            chosen_holding_id: commit-only. Must be a candidate_matches
                holding_id from the preceding evaluate, or None for a
                "no_match" outcome.
            rationale: commit-only. Must cite the evaluate response's
                clause_id when one applies.
            approval_token: commit-only for YELLOW/RED-classified cases.

        Returns:
            An evaluate result (candidate_matches, ambiguity,
            requester_pattern) or a commit result (status,
            queue_status_write, resolved_via_substitution).
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        request = repo.get_ill_request(library_id, ill_request_id)
        if request is None:
            return {"status": "error", "content": [{"text": "not_found: no ILL request with that id"}]}
        if request.status != ILLRequestStatus.OPEN:
            return {"status": "error", "content": [{"text": "already_routed"}]}

        if action == "evaluate":
            candidates = repo.search_catalog_candidates(library_id, request.requested_title, request.requested_edition_hint)
            if not candidates:
                ambiguity = "no_match"
            elif any(f in (SensitivityFlag.RARE_OR_SPECIAL_COLLECTIONS, SensitivityFlag.POLICY_EXCEPTION_REQUIRED) for f in request.flags):
                ambiguity = "policy_exception"
            elif len(candidates) == 1:
                ambiguity = "none"
            else:
                ambiguity = "multiple_editions"

            clause = None
            if ambiguity != "none":
                clauses = repo.get_policy_clauses(library_id, "ill_routing")
                clause = clauses[0].model_dump(mode="json") if clauses else None

            evaluation = {
                "ill_request_id": ill_request_id,
                "candidate_matches": [c.model_dump(mode="json") for c in candidates],
                "ambiguity": ambiguity,
                "applicable_policy_clause": clause,
                "sensitivity_flags": [f.value for f in request.flags],
                "requester_pattern": None,
            }
            cache.put(ill_request_id, evaluation)
            return {"status": "success", "content": [{"json": evaluation}]}

        if action == "commit":
            evaluation = cache.get(ill_request_id)
            if evaluation is None:
                return {"status": "error", "content": [{"text": "evaluate_not_called"}]}

            valid_ids = {c["holding_id"] for c in evaluation["candidate_matches"]}
            if chosen_holding_id is not None and chosen_holding_id not in valid_ids:
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_invalid_choice", "queue_status_write": None, "resolved_via_substitution": False}}]}

            sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
            tier = classify_ill_routing(evaluation["ambiguity"], sensitivity_flags)
            token = ApprovalToken(**approval_token) if approval_token else None
            if not is_approval_valid(tier, token.approver_role if token else None, Workflow.ILL_ROUTING):
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_missing_approval", "queue_status_write": None, "resolved_via_substitution": False}}]}

            related_action_id = f"ill_request:{ill_request_id}"
            tier_ledger.record(library_id, related_action_id, tier, Workflow.ILL_ROUTING)

            if chosen_holding_id is None:
                request.status = ILLRequestStatus.NO_MATCH
                repo.save_ill_request(request)
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "no_match_recorded", "queue_status_write": None, "resolved_via_substitution": False}}]}

            request.status = ILLRequestStatus.ROUTED
            repo.save_ill_request(request)
            queue_status_write = {"ill_request_id": ill_request_id, "chosen_holding_id": chosen_holding_id, "related_action_id": related_action_id}
            return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "committed", "queue_status_write": queue_status_write, "resolved_via_substitution": False}}]}

        return {"status": "error", "content": [{"text": f"invalid_action: {action!r}"}]}

    return route_ill_request
