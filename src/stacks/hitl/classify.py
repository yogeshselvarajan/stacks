"""The single, code-governed HITL classification function set.

This is intentionally the one place in the whole codebase that decides
GREEN vs YELLOW vs RED. See docs/architecture/final_architecture.md
section 6.2, step 3: classify() must not be talked out of its answer by
prompt phrasing, so it is plain Python, unit-tested directly, never an
LLM call.
"""
from __future__ import annotations

import enum

from stacks.types import SensitivityFlag


class Tier(str, enum.Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class Workflow(str, enum.Enum):
    ROOM_BOOKING = "room_booking"
    ILL_ROUTING = "ill_routing"
    OVERDUE_CHASE = "overdue_chase"


# Roles allowed to approve a YELLOW-tier case, per workflow. RED always
# requires exactly RED_APPROVER_ROLE, checked separately below, never via
# this table, since RED must never be satisfiable by a broader role.
YELLOW_APPROVER_ROLES: dict[Workflow, frozenset[str]] = {
    Workflow.ILL_ROUTING: frozenset({"ill_coordinator", "branch_manager"}),
    Workflow.OVERDUE_CHASE: frozenset({"circulation_staff", "branch_manager"}),
}

RED_APPROVER_ROLE = "librarian_case_review"


def classify_room_conflict(sensitivity_flags: list[SensitivityFlag]) -> Tier:
    """Room-booking resolution is binary: GREEN or RED, never YELLOW.

    final_architecture.md section 7.4 (v1 table, still the current rule
    for this workflow per architecture_options.md section 2.5 point 4:
    room-booking never left the single-agent shape and never gained a
    YELLOW tier).
    """
    return Tier.RED if sensitivity_flags else Tier.GREEN


def classify_ill_routing(
    ambiguity: str,
    sensitivity_flags: list[SensitivityFlag],
    resolved_via_substitution: bool = False,
) -> Tier:
    """ILL routing classification.

    Per tool_architecture.md section 3.3's Authorization boundary: any
    sensitivity flag is RED (consistent with the fail-closed default in
    classify_room_conflict and classify_overdue_chase). Additionally,
    ambiguity == "policy_exception" is RED regardless of flags. ambiguity
    == "none" is GREEN (when no flags present). ambiguity == "no_match"
    is classified YELLOW, since nothing auto-routes when no candidate was
    found and a human should confirm next steps rather than the case
    silently closing (Plan 1 design decision, not directly specified in
    the source docs).

    resolved_via_substitution is new this plan: when the ILL
    Disambiguation Specialist (docs/architecture/agent_architecture.md
    section 4.3) converges confidently on a substitute edition, an
    ambiguity == "multiple_editions" case is treated as GREEN, not YELLOW
    -- unless a sensitivity flag or a policy_exception ambiguity applies,
    which stay RED regardless of convergence (agent_architecture.md
    section 5.3's reconciliation, "unaffected either way"). Defaults False
    so every Plan 1 call site's behavior is unchanged.
    """
    if sensitivity_flags:
        return Tier.RED
    if ambiguity == "policy_exception":
        return Tier.RED
    if ambiguity == "none":
        return Tier.GREEN
    if ambiguity == "multiple_editions" and resolved_via_substitution:
        return Tier.GREEN
    if ambiguity in ("multiple_editions", "no_match"):
        return Tier.YELLOW
    raise ValueError(f"unrecognized ambiguity value: {ambiguity!r}")


def classify_overdue_chase(
    tier_consequence: str,
    sensitivity_flags: list[SensitivityFlag],
    has_recalled_hardship_history: bool = False,
) -> Tier:
    """Overdue-chase classification.

    Per final_architecture.md section 7.4 (v1) and tool_architecture.md
    section 3.4: collections_referral, any live sensitivity flag, or a
    recalled hardship history is RED. fee_mention/hold_block with no flag
    is YELLOW. informational with no flag is GREEN.

    has_recalled_hardship_history defaults False at Plan 1 scope -- real
    AgentCore Memory retrieval is wired in a later plan
    (agent_architecture.md section 4.4); run_overdue_chase always passes
    False explicitly until then, never omitting the parameter, so this
    function's signature does not change when Memory is wired in.
    """
    if tier_consequence == "collections_referral":
        return Tier.RED
    if sensitivity_flags:
        return Tier.RED
    if has_recalled_hardship_history:
        return Tier.RED
    if tier_consequence in ("fee_mention", "hold_block"):
        return Tier.YELLOW
    if tier_consequence == "informational":
        return Tier.GREEN
    raise ValueError(f"unrecognized tier_consequence value: {tier_consequence!r}")


def is_approval_valid(tier: Tier, approver_role: str | None, workflow: Workflow) -> bool:
    """Whether a supplied approver_role satisfies the given tier's
    requirement.

    Called independently by both the HITL gate hook (Task 6) and by each
    gated tool's own commit path (defense in depth) -- tool_architecture.md
    section 3.2's Authorization boundary: "a token with only a general ...
    role, even if supplied, is rejected for a RED case," checked in the
    tool itself, not only by the hook.
    """
    if tier is Tier.GREEN:
        return True
    if approver_role is None:
        return False
    if tier is Tier.RED:
        return approver_role == RED_APPROVER_ROLE
    if tier is Tier.YELLOW:
        allowed = YELLOW_APPROVER_ROLES.get(workflow, frozenset())
        return approver_role in allowed
    raise ValueError(f"unrecognized tier: {tier!r}")
