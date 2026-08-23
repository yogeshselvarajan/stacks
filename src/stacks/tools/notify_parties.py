"""notify_parties -- the single centralized send, Guardrail-checked and
token-gated. See docs/architecture/tool_architecture.md section 3.5.
"""
from __future__ import annotations

import re
from typing import Any

from strands import tool

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.classify import Tier, is_approval_valid
from stacks.hitl.tier_ledger import TierLedger
from stacks.types import ApprovalToken

_GUARDRAIL_DENYLIST = ("social security number", "ssn:", "credit card")

_ELEVATED_SEVERITY_KEYWORDS = (
    "fee", "fine", "charge",
    "hold", "blocked", "suspended", "restricted",
    "collections", "collection agency", "legal action", "referred to collections",
)


class NotificationSink:
    """Plan 1 in-memory notification sink -- records what would have been
    sent. A real SES-backed sink is an AWS-infrastructure follow-on task."""

    def __init__(self) -> None:
        self._sent: list[dict[str, Any]] = []

    def send(self, recipients: list[str], subject: str, body: str) -> str:
        notification_id = f"notif_{len(self._sent) + 1}"
        self._sent.append({"notification_id": notification_id, "recipients": recipients, "subject": subject, "body": body})
        return notification_id

    def all(self) -> list[dict[str, Any]]:
        return list(self._sent)


def make_notify_parties(repo: LibraryDataRepository, sink: NotificationSink, tier_ledger: TierLedger, session_library_id: str):
    @tool
    def notify_parties(
        library_id: str,
        related_action_id: str,
        subject: str,
        body: str,
        approval_token: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a notification tied to an already-committed workflow action.

        Args:
            library_id: Tenant scope.
            related_action_id: The resolve/route/chase commit this send is
                authorized by, e.g. "room_conflict:b1:b2".
            subject: Notification subject line.
            body: LLM-composed notification body; always passed through the
                Guardrail check regardless of the related action's own tier.
            approval_token: Required when the related action's tier is
                YELLOW or RED.

        Returns:
            A result with status "sent", "blocked_by_guardrail",
            "blocked_missing_approval", or "blocked_unauthorized_recipient".
        """
        # Cross-tenant denial check (first gate)
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        findings = _guardrail_check(subject, body)
        if findings:
            return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_by_guardrail", "guardrail_findings": findings}}]}

        tier_entry = tier_ledger.get(library_id, related_action_id)
        if tier_entry is None:
            return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_missing_approval", "guardrail_findings": None}}]}
        tier, workflow = tier_entry

        if tier is Tier.GREEN:
            severity_findings = _elevated_severity_check(subject, body)
            if severity_findings:
                return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_by_guardrail", "guardrail_findings": severity_findings}}]}

        token = None
        if approval_token:
            try:
                token = ApprovalToken(**approval_token)
            except Exception:
                # Malformed token: treat as no token supplied
                token = None

        if token is not None and token.related_action_id != related_action_id:
            return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_unauthorized_recipient", "guardrail_findings": None}}]}
        if not is_approval_valid(tier, token.approver_role if token else None, workflow):
            return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_missing_approval", "guardrail_findings": None}}]}

        recipients = _derive_recipients(repo, library_id, related_action_id)
        if not recipients:
            return {"status": "success", "content": [{"json": {"notification_id": None, "status": "blocked_unauthorized_recipient", "guardrail_findings": None}}]}

        notification_id = sink.send(recipients, subject, body)
        return {"status": "success", "content": [{"json": {"notification_id": notification_id, "status": "sent", "guardrail_findings": None}}]}

    return notify_parties


def _guardrail_check(subject: str, body: str) -> list[str]:
    """Plan 1 stand-in for Bedrock Guardrails -- a fixed denylist a real
    Guardrail policy would also block. Replaced by a real ApplyGuardrail
    call in the AWS-infrastructure follow-on task; the call site
    (unconditional, before every send) does not change.
    """
    combined = f"{subject}\n{body}".lower()
    return [f"blocked_pattern: {p}" for p in _GUARDRAIL_DENYLIST if p in combined]


def _elevated_severity_check(subject: str, body: str) -> list[str]:
    """When the related action's tier is GREEN (no human ever reviewed it),
    also block elevated-severity language in subject+body -- e.g. a
    collections-threat body attached to an unreviewed informational
    overdue notice. Word-boundary matched, reusing run_overdue_chase.py's
    keyword set and matching pattern (tool_architecture.md section 3.5's
    Authorization boundary, whole-branch review Important 1).
    """
    combined = f"{subject}\n{body}".lower()
    findings = []
    for keyword in _ELEVATED_SEVERITY_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", combined):
            findings.append(f"blocked_pattern: {keyword}")
    return findings


def _derive_recipients(repo: LibraryDataRepository, library_id: str, related_action_id: str) -> list[str]:
    """Derives recipients from related_action_id's own underlying record --
    never accepted as an input field (tool_architecture.md section 3.5).
    """
    kind, _, case_id = related_action_id.partition(":")
    if kind == "room_conflict":
        booking_ids = case_id.split(":")
        bookings = [repo.get_booking(library_id, bid) for bid in booking_ids]
        # Fail closed if any booking is None (don't silently drop)
        if any(b is None for b in bookings):
            return []
        recipients = [b.booked_by for b in bookings]
        # Deduplicate while preserving order
        return list(dict.fromkeys(recipients))
    if kind == "ill_request":
        request = repo.get_ill_request(library_id, case_id)
        return [request.requester_patron_id] if request is not None else []
    if kind == "overdue":
        record = repo.get_circulation_record(library_id, case_id)
        return [record.patron_id] if record is not None else []
    return []
