"""HITL gate hook -- the single BeforeToolCallEvent choke point that runs
classify() and raises a Strands interrupt for YELLOW/RED cases. See
docs/architecture/final_architecture.md section 6.2 and
docs/architecture/tool_architecture.md section 1 ("Single HITL choke point").
"""
from __future__ import annotations

from typing import Any

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry
from strands.interrupt import InterruptException

from stacks.hitl.classify import (
    Tier,
    Workflow,
    classify_ill_routing,
    classify_overdue_chase,
    classify_room_conflict,
    is_approval_valid,
)
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.types import SensitivityFlag

# Tool names whose "commit" action is HITL-gated, and which workflow
# applies. notify_parties is deliberately absent -- its own gating is
# keyed to the tier of the action it's attached to, not gated a second
# time here (tool_architecture.md section 3.5).
_GATED_COMMIT_TOOLS: dict[str, Workflow] = {
    "resolve_room_conflict": Workflow.ROOM_BOOKING,
    "route_ill_request": Workflow.ILL_ROUTING,
    "run_overdue_chase": Workflow.OVERDUE_CHASE,
}


class HitlGateHook(HookProvider):
    """Intercepts every commit-mode call to a gated tool, re-derives its
    tier from the same EvaluationCache the tool itself populated, and
    raises a Strands interrupt for YELLOW/RED. Shares its three
    EvaluationCache instances with agent.py's tool wiring (Task 11) so it
    is reasoning over the exact same deterministic facts evaluate already
    computed, never a second independent judgment.
    """

    def __init__(
        self,
        room_conflict_cache: EvaluationCache,
        ill_cache: EvaluationCache,
        overdue_cache: EvaluationCache,
    ) -> None:
        self._caches: dict[Workflow, EvaluationCache] = {
            Workflow.ROOM_BOOKING: room_conflict_cache,
            Workflow.ILL_ROUTING: ill_cache,
            Workflow.OVERDUE_CHASE: overdue_cache,
        }

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self._gate)

    def _gate(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]
        workflow = _GATED_COMMIT_TOOLS.get(tool_name)
        if workflow is None:
            return

        tool_input = event.tool_use["input"]
        if tool_input.get("action") != "commit":
            return

        try:
            library_id = tool_input.get("library_id")
            case_id = _case_id_for(workflow, tool_input)
            related_action_id = _related_action_id_for(workflow, case_id)
            evaluation = self._caches[workflow].get(library_id, case_id)
            if evaluation is None:
                # No preceding evaluate cached -- the gate cannot determine
                # safety and must not guess. Block the call.
                event.cancel_tool = "blocked_missing_evaluation"
                return

            tier = _classify_from_evaluation(workflow, evaluation, tool_input)
            # A genuinely tied ROOM_BOOKING case requires an approval token
            # from the tool itself regardless of tier (resolve_room_conflict's
            # own fix) -- so a tied GREEN case must still fall through to the
            # interrupt block below, or no human is ever asked and the case
            # becomes an unresolvable dead end. A non-tied GREEN case still
            # returns early as before. Whole-branch review Important 5.
            is_unresolvable_tie = workflow is Workflow.ROOM_BOOKING and evaluation.get("tie")
            if tier is Tier.GREEN and not is_unresolvable_tie:
                return

            approval_token = tool_input.get("approval_token")
            approver_role = approval_token.get("approver_role") if approval_token else None
            token_related_action_id = approval_token.get("related_action_id") if approval_token else None
            if is_approval_valid(tier, approver_role, workflow) and token_related_action_id == related_action_id:
                return
        except Exception as exc:
            event.cancel_tool = "blocked_gate_error"
            return

        try:
            response = event.interrupt(
                f"hitl:{tool_name}:{case_id}",
                reason={"tier": tier.value, "tool": tool_name, "workflow": workflow.value, "case_id": case_id},
            )
            if not isinstance(response, dict) or not response.get("approved"):
                event.cancel_tool = f"blocked_missing_approval: tier={tier.value}"
                return

            resumed_role = response.get("approver_role")
            if not is_approval_valid(tier, resumed_role, workflow):
                event.cancel_tool = f"blocked_missing_approval: tier={tier.value}"
                return

            tool_input["approval_token"] = {
                "token": response.get("token", f"hitl_resume:{case_id}"),
                "approver_role": resumed_role,
                "related_action_id": related_action_id,
            }
        except InterruptException:
            raise


def _case_id_for(workflow: Workflow, tool_input: dict[str, Any]) -> str:
    if workflow is Workflow.ROOM_BOOKING:
        return ":".join(sorted(tool_input["conflicting_booking_ids"]))
    if workflow is Workflow.ILL_ROUTING:
        return tool_input["ill_request_id"]
    if workflow is Workflow.OVERDUE_CHASE:
        return tool_input["circulation_record_id"]
    raise ValueError(f"unrecognized workflow: {workflow!r}")


def _related_action_id_for(workflow: Workflow, case_id: str) -> str:
    if workflow is Workflow.ROOM_BOOKING:
        return f"room_conflict:{case_id}"
    if workflow is Workflow.ILL_ROUTING:
        return f"ill_request:{case_id}"
    if workflow is Workflow.OVERDUE_CHASE:
        return f"overdue:{case_id}"
    raise ValueError(f"unrecognized workflow: {workflow!r}")


def _classify_from_evaluation(
    workflow: Workflow, evaluation: dict[str, Any], tool_input: dict[str, Any] | None = None
) -> Tier:
    sensitivity_flags = [SensitivityFlag(f) for f in evaluation["sensitivity_flags"]]
    if workflow is Workflow.ROOM_BOOKING:
        return classify_room_conflict(sensitivity_flags)
    if workflow is Workflow.ILL_ROUTING:
        # resolved_via_substitution is only known at commit time (the
        # specialist runs between evaluate and commit), so it is read from
        # the commit call's own tool_input, never from the cached
        # evaluation, which was computed before the specialist ran.
        #
        # "Resolved via substitution" is definitionally a claim about
        # having converged on a specific holding -- a commit with no
        # chosen_holding_id (a no-match outcome) can never honestly be
        # "resolved", regardless of the caller's flag. This mirrors
        # route_ill_request's own effective_resolved_via_substitution
        # guard exactly: both sites must agree, or the gate and the tool
        # disagree about the tier.
        ill_tool_input = tool_input or {}
        resolved_via_substitution = (
            bool(ill_tool_input.get("resolved_via_substitution"))
            and ill_tool_input.get("chosen_holding_id") is not None
        )
        return classify_ill_routing(evaluation["ambiguity"], sensitivity_flags, resolved_via_substitution)
    if workflow is Workflow.OVERDUE_CHASE:
        return classify_overdue_chase(
            evaluation["tier_consequence"], sensitivity_flags, evaluation.get("has_recalled_hardship_history", False)
        )
    raise ValueError(f"unrecognized workflow: {workflow!r}")
