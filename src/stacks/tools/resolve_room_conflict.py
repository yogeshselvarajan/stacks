"""resolve_room_conflict -- policy-aware reasoning and gated commit for the
room-booking workflow. See docs/architecture/tool_architecture.md section
3.2 for the full spec this implements.
"""
from __future__ import annotations

from typing import Any

from strands import tool

from stacks.data.models import BookingRecord
from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Workflow, classify_room_conflict, is_approval_valid
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.types import ApprovalToken, SensitivityFlag

_PRIORITY = {"recurring_program": 3, "staff_internal": 2, "one_off_renter": 1, "walk_in": 0}


def make_resolve_room_conflict(
    repo: LibraryDataRepository,
    cache: EvaluationCache,
    tier_ledger: TierLedger,
    session_library_id: str,
):
    @tool
    def resolve_room_conflict(
        library_id: str,
        action: str,
        conflicting_booking_ids: list[str],
        chosen_resolution_booking_id: str | None = None,
        rationale: str | None = None,
        approval_token: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate or commit a resolution for an overlapping room-booking
        conflict.

        Args:
            library_id: Tenant scope; must match the session's own library_id.
            action: "evaluate" or "commit".
            conflicting_booking_ids: The two or more booking ids that overlap.
            chosen_resolution_booking_id: commit-only. Which booking yields;
                must equal one of the immediately preceding evaluate call's
                candidate booking_id_that_yields values.
            rationale: commit-only. Must cite the evaluate response's clause_id.
            approval_token: commit-only for a sensitivity-flagged conflict.
                Shape: token, approver_role, related_action_id.

        Returns:
            An evaluate result (candidate_resolutions, sensitivity_flags) or
            a commit result (status, calendar_write).
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        conflict_id = ":".join(sorted(conflicting_booking_ids))
        bookings = [repo.get_booking(library_id, bid) for bid in conflicting_booking_ids]
        if any(b is None for b in bookings):
            return {"status": "error", "content": [{"text": "not_found: one or more booking ids do not exist"}]}

        if not _bookings_overlap(bookings):
            return {"status": "error", "content": [{"text": "no_conflict_detected: named bookings do not overlap"}]}

        if action == "evaluate":
            clauses = repo.get_policy_clauses(library_id, "room_booking_priority")
            if not clauses:
                return {"status": "error", "content": [{"text": "policy_not_found"}]}
            clause = clauses[0]
            candidates = _rank_resolutions(bookings, clause.clause_id)
            sensitivity_flags = sorted({f for b in bookings for f in b.flags}, key=lambda f: f.value)
            evaluation = {
                "conflict_id": conflict_id,
                "applicable_policy_clause": clause.model_dump(mode="json"),
                "candidate_resolutions": candidates,
                "sensitivity_flags": [f.value for f in sensitivity_flags],
                "tie": len(candidates) >= 2 and candidates[0]["deterministic_score"] == candidates[1]["deterministic_score"],
            }
            cache.put(conflict_id, evaluation)
            return {"status": "success", "content": [{"json": evaluation}]}

        if action == "commit":
            evaluation = cache.get(conflict_id)
            if evaluation is None:
                return {"status": "error", "content": [{"text": "evaluate_not_called: commit requires a preceding evaluate for this conflict_id"}]}

            valid_ids = {c["booking_id_that_yields"] for c in evaluation["candidate_resolutions"]}
            if chosen_resolution_booking_id not in valid_ids:
                return {"status": "success", "content": [{"json": {"conflict_id": conflict_id, "status": "blocked_invalid_choice", "calendar_write": None}}]}

            clause_id = evaluation["applicable_policy_clause"]["clause_id"]
            if not rationale or clause_id not in rationale:
                return {"status": "success", "content": [{"json": {"conflict_id": conflict_id, "status": "blocked_invalid_choice", "calendar_write": None}}]}

            sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
            tier = classify_room_conflict(sensitivity_flags)
            token = ApprovalToken(**approval_token) if approval_token else None
            if not is_approval_valid(tier, token.approver_role if token else None, Workflow.ROOM_BOOKING):
                return {"status": "success", "content": [{"json": {"conflict_id": conflict_id, "status": "blocked_missing_approval", "calendar_write": None}}]}

            yielding_booking = next(b for b in bookings if b.booking_id == chosen_resolution_booking_id)
            repo.save_booking(_apply_yield(yielding_booking))

            related_action_id = f"room_conflict:{conflict_id}"
            tier_ledger.record(related_action_id, tier, Workflow.ROOM_BOOKING)
            calendar_write = {"conflict_id": conflict_id, "yielding_booking_id": chosen_resolution_booking_id, "related_action_id": related_action_id}
            return {"status": "success", "content": [{"json": {"conflict_id": conflict_id, "status": "committed", "calendar_write": calendar_write}}]}

        return {"status": "error", "content": [{"text": f"invalid_action: {action!r}"}]}

    return resolve_room_conflict


def _bookings_overlap(bookings: list[BookingRecord]) -> bool:
    for i, a in enumerate(bookings):
        for b in bookings[i + 1:]:
            if a.room_id == b.room_id and a.start < b.end and b.start < a.end:
                return True
    return False


def _rank_resolutions(bookings: list[BookingRecord], clause_id: str) -> list[dict[str, Any]]:
    ranked = sorted(bookings, key=lambda b: _PRIORITY[b.booking_type.value], reverse=True)
    keeper, yielder = ranked[0], ranked[-1]
    score = float(_PRIORITY[keeper.booking_type.value] - _PRIORITY[yielder.booking_type.value])
    return [{
        "booking_id_that_yields": yielder.booking_id,
        "booking_id_that_keeps": keeper.booking_id,
        "deterministic_score": score,
        "rule_applied": clause_id,
    }]


def _apply_yield(booking: BookingRecord) -> BookingRecord:
    booking.notes = (booking.notes + " [yielded per priority policy]").strip()
    return booking
