"""Workflow-scoped access: which staff role owns which operational
workflow. Mirrors frontend/components/app-shell.tsx's ROLE_VISIBLE_ROUTES
table exactly, kept as a plain, framework-free function per this
project's own convention (see classify() in src/stacks/hitl/classify.py)
of keeping business rules independent of the web framework that later
enforces them.
"""
from __future__ import annotations

WORKFLOW_OWNING_ROLE: dict[str, str] = {
    "room_booking": "room_booking_staff",
    "ill_routing": "ill_coordinator",
    "overdue_chase": "circulation_staff",
}


def role_can_access_workflow(role: str, workflow: str) -> bool:
    if role == "branch_manager":
        return True
    return role == WORKFLOW_OWNING_ROLE[workflow]
