import os

import pytest

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.classify import Tier, Workflow
from stacks.hitl.tier_ledger import TierLedger
from stacks.tools.notify_parties import NotificationSink, make_notify_parties


def _build(session_library_id="lib_demo"):
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    seed_demo_library(repo, library_id="lib_other")
    sink = NotificationSink()
    tier_ledger = TierLedger()
    tool_fn = make_notify_parties(repo, sink, tier_ledger, session_library_id)
    return tool_fn, repo, sink, tier_ledger


def test_green_action_sends_without_approval_token():
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "room_conflict:b_oneoff_a:b_recurring_a", Tier.GREEN, Workflow.ROOM_BOOKING)
    result = tool_fn(library_id="lib_demo", related_action_id="room_conflict:b_oneoff_a:b_recurring_a", subject="Booking update", body="Your booking has changed.")
    body = result["content"][0]["json"]
    assert body["status"] == "sent"
    assert len(sink.all()) == 1
    assert set(sink.all()[0]["recipients"]) == {"patron_recurring", "patron_renter"}


def test_sends_with_a_sensible_default_when_the_model_omits_subject_and_body():
    """Found live against the real deployed AgentCore Runtime, 2026-09-14:
    Nova Lite twice called notify_parties with only library_id and
    related_action_id, omitting subject and body -- both were previously
    required parameters with no default, so the call failed validation
    before it could send anything, even though the related action had
    already genuinely committed. A prompt-only fix (telling the model to
    always include them) did not change this live-observed behavior, so
    the tool itself now degrades to a real, generic notification instead
    of failing outright."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "room_conflict:b_oneoff_a:b_recurring_a", Tier.GREEN, Workflow.ROOM_BOOKING)
    result = tool_fn(library_id="lib_demo", related_action_id="room_conflict:b_oneoff_a:b_recurring_a")
    body = result["content"][0]["json"]
    assert body["status"] == "sent"
    assert len(sink.all()) == 1
    sent = sink.all()[0]
    assert sent["subject"]
    assert sent["body"]


def test_yellow_action_requires_valid_approval_token():
    tool_fn, _, _, tier_ledger = _build()
    tier_ledger.record("lib_demo", "ill_request:ill_ambiguous", Tier.YELLOW, Workflow.ILL_ROUTING)
    blocked = tool_fn(library_id="lib_demo", related_action_id="ill_request:ill_ambiguous", subject="ILL update", body="Your request is being reviewed.")
    assert blocked["content"][0]["json"]["status"] == "blocked_missing_approval"

    sent = tool_fn(
        library_id="lib_demo", related_action_id="ill_request:ill_ambiguous", subject="ILL update", body="Your request is being reviewed.",
        approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_ambiguous"},
    )
    assert sent["content"][0]["json"]["status"] == "sent"


def test_recipients_are_not_accepted_as_input():
    """notify_parties has no recipients parameter at all -- attempting to
    pass one is simply ignored by Python's keyword handling, proving the
    tool signature itself has no such field to exploit."""
    import inspect
    tool_fn, _, _, _ = _build()
    sig = inspect.signature(tool_fn)
    assert "recipients" not in sig.parameters


def test_related_action_with_no_recorded_tier_is_blocked():
    tool_fn, _, _, _ = _build()
    result = tool_fn(library_id="lib_demo", related_action_id="room_conflict:does_not_exist", subject="x", body="y")
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_guardrail_check_blocks_flagged_content():
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    result = tool_fn(library_id="lib_demo", related_action_id="overdue:circ_green", subject="Reminder", body="Please provide your Social Security Number to confirm.")
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_by_guardrail"
    assert body["guardrail_findings"]
    assert sink.all() == []


def test_cross_tenant_denial():
    """Calling with a library_id different from session_library_id returns cross_tenant_denied."""
    tool_fn, _, _, tier_ledger = _build(session_library_id="lib_demo")
    tier_ledger.record("lib_demo", "room_conflict:b_oneoff_a:b_recurring_a", Tier.GREEN, Workflow.ROOM_BOOKING)
    result = tool_fn(library_id="lib_other", related_action_id="room_conflict:b_oneoff_a:b_recurring_a", subject="x", body="y")
    assert result["status"] == "error"
    assert result["content"][0]["text"] == "cross_tenant_denied"


def test_tier_ledger_cross_tenant_isolation():
    """Record a tier for lib_a under some related_action_id, then call notify_parties
    with lib_b and the same related_action_id -- it must NOT find lib_a's tier."""
    tool_fn, _, _, tier_ledger = _build(session_library_id="lib_demo")
    # Record a tier for lib_other
    tier_ledger.record("lib_other", "room_conflict:b_oneoff_a:b_recurring_a", Tier.GREEN, Workflow.ROOM_BOOKING)
    # Try to call with lib_demo (different library) - should not find the tier
    result = tool_fn(library_id="lib_demo", related_action_id="room_conflict:b_oneoff_a:b_recurring_a", subject="x", body="y")
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_token_mismatch_related_action_id():
    """A token whose related_action_id doesn't match is rejected."""
    tool_fn, _, _, tier_ledger = _build()
    tier_ledger.record("lib_demo", "ill_request:ill_ambiguous", Tier.YELLOW, Workflow.ILL_ROUTING)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="ill_request:ill_ambiguous",
        subject="x",
        body="y",
        approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:different_id"},
    )
    assert result["content"][0]["json"]["status"] == "blocked_unauthorized_recipient"


def test_red_tier_requires_exact_approver_role():
    """RED tier requires the exact approver role - a wrong role is rejected."""
    tool_fn, _, _, tier_ledger = _build()
    tier_ledger.record("lib_demo", "room_conflict:b_oneoff_a:b_recurring_a", Tier.RED, Workflow.ROOM_BOOKING)
    # Try with wrong role (branch_manager instead of librarian_case_review)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="room_conflict:b_oneoff_a:b_recurring_a",
        subject="x",
        body="y",
        approval_token={"token": "t", "approver_role": "branch_manager", "related_action_id": "room_conflict:b_oneoff_a:b_recurring_a"},
    )
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_malformed_approval_token_does_not_raise():
    """A malformed approval_token dict does not raise - it's treated as no token."""
    tool_fn, _, _, tier_ledger = _build()
    tier_ledger.record("lib_demo", "ill_request:ill_ambiguous", Tier.YELLOW, Workflow.ILL_ROUTING)
    # Pass a malformed token (missing required fields)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="ill_request:ill_ambiguous",
        subject="x",
        body="y",
        approval_token={"incomplete": "token"},
    )
    # Should be blocked_missing_approval (no valid token), not raise
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_guardrail_blocks_flagged_subject():
    """A clean body with a flagged subject (e.g. SSN request) is blocked by guardrail."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="overdue:circ_green",
        subject="Please send your Social Security Number",
        body="Normal reminder text",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_by_guardrail"
    assert body["guardrail_findings"]
    assert sink.all() == []


def test_green_tier_blocks_collections_threat_body():
    """A GREEN-tier action (nobody ever reviewed it) with an unapproved
    collections-threat body must be blocked, not sent -- whole-branch
    review Important 1."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="overdue:circ_green",
        subject="Overdue reminder",
        body="Your account will be referred to collections if not resolved.",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_by_guardrail"
    assert body["guardrail_findings"]
    assert sink.all() == []


def test_green_tier_allows_genuinely_informational_content():
    """A GREEN-tier action with genuinely informational content still
    sends -- the new elevated-severity check must not over-block."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="overdue:circ_green",
        subject="Friendly reminder",
        body="Your item is now overdue. Please return it at your earliest convenience.",
    )
    body = result["content"][0]["json"]
    assert body["status"] == "sent"
    assert len(sink.all()) == 1


def test_red_tier_with_valid_approval_allows_collections_language():
    """A RED-tier action with a valid approval token still sends even with
    collections language -- it went through real human approval, so the
    GREEN-only elevated-severity check must not apply."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.RED, Workflow.OVERDUE_CHASE)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="overdue:circ_green",
        subject="Final notice",
        body="Your account has been referred to collections per policy OES-3.",
        approval_token={"token": "t", "approver_role": "librarian_case_review", "related_action_id": "overdue:circ_green"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "sent"
    assert len(sink.all()) == 1


def test_room_conflict_with_missing_booking_fails_closed():
    """A room-conflict related_action_id where one of the two bookings can't be found
    returns blocked_unauthorized_recipient, not a partial send."""
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "room_conflict:b_oneoff_a:nonexistent", Tier.GREEN, Workflow.ROOM_BOOKING)
    result = tool_fn(
        library_id="lib_demo",
        related_action_id="room_conflict:b_oneoff_a:nonexistent",
        subject="x",
        body="y",
    )
    assert result["content"][0]["json"]["status"] == "blocked_unauthorized_recipient"
    assert sink.all() == []


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and a provisioned Bedrock Guardrail. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_real_bedrock_guardrail_blocks_ssn_content_live():
    """Proves the real Guardrail (not the denylist stand-in) actually
    blocks live, per final_problem_selection.md's stretch goal: 'demonstrated
    blocking something live in the demo, not just declared in a config file'.
    Run: STACKS_BEDROCK_GUARDRAIL_ID=<id> STACKS_BEDROCK_GUARDRAIL_VERSION=<v>
      RUN_LIVE_BEDROCK_TESTS=1 pytest tests/unit/test_notify_parties.py -k live
    """
    from stacks.guardrails.bedrock_guardrail import BedrockGuardrailClient

    guardrail_client = BedrockGuardrailClient(
        guardrail_id=os.environ["STACKS_BEDROCK_GUARDRAIL_ID"],
        guardrail_version=os.environ["STACKS_BEDROCK_GUARDRAIL_VERSION"],
        region=os.environ.get("STACKS_AWS_REGION", "us-west-2"),
    )
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("lib_demo", "overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    # Rebuild the tool with the real guardrail client wired in.
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    tool_fn = make_notify_parties(repo, sink, tier_ledger, "lib_demo", guardrail_client=guardrail_client)

    blocked = tool_fn(
        library_id="lib_demo", related_action_id="overdue:circ_green",
        subject="Reminder", body="Please provide your Social Security Number to confirm.",
    )
    assert blocked["content"][0]["json"]["status"] == "blocked_by_guardrail"
    assert blocked["content"][0]["json"]["guardrail_findings"]
    assert sink.all() == []

    clean = tool_fn(
        library_id="lib_demo", related_action_id="overdue:circ_green",
        subject="Reminder", body="Your item is overdue, please return it soon.",
    )
    assert clean["content"][0]["json"]["status"] == "sent"
