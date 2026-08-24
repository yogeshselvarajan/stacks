"""route_ill_request -- evaluate/commit for ambiguous ILL routing.

commit accepts a resolved_via_substitution flag, set by the calling agent
from the ILL Disambiguation Specialist's own ILLDisambiguationResult
(stacks.tools.disambiguate_ill_candidates), which lets a confidently
converged "multiple_editions" case commit at GREEN instead of YELLOW (see
classify_ill_routing). See docs/architecture/tool_architecture.md
section 3.3.

This flag is never trusted as the model passed it: commit verifies it
against disambiguation_cache, the code-held record of the specialist's
own convergence result, via stacks.hitl.ill_disambiguation_verification.
A claim with no corresponding cache entry (disambiguate_ill_candidates
was never called for this case) is always reduced to False (whole-branch
review Critical 1).
"""
from __future__ import annotations

from typing import Any

from strands import tool

from stacks.data.models import ILLRequestStatus
from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Workflow, classify_ill_routing, is_approval_valid
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.ill_disambiguation_verification import verify_resolved_via_substitution
from stacks.hitl.tier_ledger import TierLedger
from stacks.memory.store import MemoryStore
from stacks.types import ApprovalToken, SensitivityFlag


def make_route_ill_request(
    repo: LibraryDataRepository,
    cache: EvaluationCache,
    tier_ledger: TierLedger,
    session_library_id: str,
    memory: MemoryStore,
    disambiguation_cache: EvaluationCache,
):
    @tool
    def route_ill_request(
        library_id: str,
        ill_request_id: str,
        action: str,
        chosen_holding_id: str | None = None,
        rationale: str | None = None,
        resolved_via_substitution: bool = False,
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
            resolved_via_substitution: commit-only. True when the ILL
                Disambiguation Specialist converged confidently on
                chosen_holding_id for an originally "multiple_editions"
                case. The agent sets this based on the specialist's own
                ILLDisambiguationResult -- never invented independently of
                that result. This claim is verified, not trusted: it only
                takes effect when disambiguation_cache actually holds a
                matching convergence record from a real
                disambiguate_ill_candidates call for this ill_request_id.
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
            if any(f in (SensitivityFlag.RARE_OR_SPECIAL_COLLECTIONS, SensitivityFlag.POLICY_EXCEPTION_REQUIRED) for f in request.flags):
                ambiguity = "policy_exception"
            elif not candidates:
                ambiguity = "no_match"
            elif len(candidates) == 1:
                ambiguity = "none"
            else:
                ambiguity = "multiple_editions"

            clause = None
            if ambiguity != "none":
                clauses = repo.get_policy_clauses(library_id, "ill_routing")
                clause = clauses[0].model_dump(mode="json") if clauses else None

            try:
                requester_pattern = memory.get_ill_substitution_pattern(library_id, request.requester_patron_id)
                requester_pattern_json = requester_pattern.model_dump(mode="json") if requester_pattern else None
            except Exception:
                requester_pattern_json = None  # fail-open: treated identically to a first-time requester

            evaluation = {
                "ill_request_id": ill_request_id,
                "candidate_matches": [c.model_dump(mode="json") for c in candidates],
                "ambiguity": ambiguity,
                "applicable_policy_clause": clause,
                "sensitivity_flags": [f.value for f in request.flags],
                "requester_pattern": requester_pattern_json,
                "requester_patron_id": request.requester_patron_id,
            }
            cache.put(library_id, ill_request_id, evaluation)
            return {"status": "success", "content": [{"json": evaluation}]}

        if action == "commit":
            evaluation = cache.get(library_id, ill_request_id)
            if evaluation is None:
                return {"status": "error", "content": [{"text": "evaluate_not_called"}]}

            # "Resolved via substitution" is definitionally a claim about
            # having converged on a specific holding -- a commit with no
            # chosen_holding_id (a no-match outcome) can never honestly be
            # "resolved", regardless of what the caller passed. It is also
            # never trusted from the caller's bare claim alone: it is only
            # True when disambiguation_cache actually holds the ILL
            # Disambiguation Specialist's own convergence record for this
            # exact (library_id, ill_request_id), confidently pointing at
            # this exact chosen_holding_id (whole-branch review Critical
            # 1 -- see stacks.hitl.ill_disambiguation_verification for the
            # full rule). Computed once, up front, and used consistently
            # for both tier classification and every returned
            # resolved_via_substitution field below, so no branch can ever
            # report True when nothing was actually, verifiably
            # substituted. Without the cache check, resolved_via_substitution=True
            # with a chosen_holding_id but no preceding disambiguate_ill_candidates
            # call would classify at GREEN purely on the model's own
            # unverified claim, with no human ever asked.
            effective_resolved_via_substitution = verify_resolved_via_substitution(
                disambiguation_cache, library_id, ill_request_id, chosen_holding_id, resolved_via_substitution,
            )

            valid_ids = {c["holding_id"] for c in evaluation["candidate_matches"]}
            if chosen_holding_id is not None and chosen_holding_id not in valid_ids:
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_invalid_choice", "queue_status_write": None, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}

            # Validate rationale cites applicable policy clause (when present)
            applicable_clause = evaluation["applicable_policy_clause"]
            if applicable_clause is not None:
                clause_id = applicable_clause["clause_id"]
                if not rationale or clause_id not in rationale:
                    return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_invalid_choice", "queue_status_write": None, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}

            sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
            tier = classify_ill_routing(evaluation["ambiguity"], sensitivity_flags, effective_resolved_via_substitution)

            # Compute related_action_id before approval check
            related_action_id = f"ill_request:{ill_request_id}"

            # Parse and validate approval token (with fallback for malformed)
            token = None
            if approval_token:
                try:
                    token = ApprovalToken(**approval_token)
                    # Validate token's related_action_id matches computed one
                    if token.related_action_id != related_action_id:
                        return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_missing_approval", "queue_status_write": None, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}
                except Exception:
                    # Malformed token: treat as no token supplied
                    token = None

            if not is_approval_valid(tier, token.approver_role if token else None, Workflow.ILL_ROUTING):
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "blocked_missing_approval", "queue_status_write": None, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}

            tier_ledger.record(library_id, related_action_id, tier, Workflow.ILL_ROUTING)

            if chosen_holding_id is None:
                request.status = ILLRequestStatus.NO_MATCH
                repo.save_ill_request(request)
                # effective_resolved_via_substitution is always False here
                # (chosen_holding_id is None), so this never reports the
                # caller's raw claim as fact when nothing was substituted.
                return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "no_match_recorded", "queue_status_write": None, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}

            request.status = ILLRequestStatus.ROUTED
            repo.save_ill_request(request)
            queue_status_write = {"ill_request_id": ill_request_id, "chosen_holding_id": chosen_holding_id, "related_action_id": related_action_id}
            return {"status": "success", "content": [{"json": {"ill_request_id": ill_request_id, "status": "committed", "queue_status_write": queue_status_write, "resolved_via_substitution": effective_resolved_via_substitution, "requester_patron_id": evaluation["requester_patron_id"], "subject_area": None}}]}

        return {"status": "error", "content": [{"text": f"invalid_action: {action!r}"}]}

    return route_ill_request
