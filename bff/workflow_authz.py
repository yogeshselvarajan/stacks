# bff/workflow_authz.py
"""Workflow-scoped authorization dependencies. Mirrors the frontend's
own already-tested ROLE_VISIBLE_ROUTES table (frontend/components/
app-shell.tsx) server-side, so the backend actually enforces what the
navigation only implies. Each function raises 403 when the caller's
role has no business in that workflow; branch_manager always passes,
per role_can_access_workflow's own rule.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from stacks.identity.claims import StaffIdentityClaims
from stacks.identity.workflow_access import role_can_access_workflow

from bff.deps import get_current_claims


def require_room_booking_access(claims: StaffIdentityClaims = Depends(get_current_claims)) -> None:
    if not role_can_access_workflow(claims.role, "room_booking"):
        raise HTTPException(status_code=403, detail="your role cannot access this workflow")


def require_ill_access(claims: StaffIdentityClaims = Depends(get_current_claims)) -> None:
    if not role_can_access_workflow(claims.role, "ill_routing"):
        raise HTTPException(status_code=403, detail="your role cannot access this workflow")


def require_overdue_access(claims: StaffIdentityClaims = Depends(get_current_claims)) -> None:
    if not role_can_access_workflow(claims.role, "overdue_chase"):
        raise HTTPException(status_code=403, detail="your role cannot access this workflow")


def require_approvals_access(claims: StaffIdentityClaims = Depends(get_current_claims)) -> None:
    if claims.role != "branch_manager" and claims.case_review_role is None:
        raise HTTPException(status_code=403, detail="your role cannot access this workflow")
