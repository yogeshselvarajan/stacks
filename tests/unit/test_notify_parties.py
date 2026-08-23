from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.classify import Tier, Workflow
from stacks.hitl.tier_ledger import TierLedger
from stacks.tools.notify_parties import NotificationSink, make_notify_parties


def _build():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    sink = NotificationSink()
    tier_ledger = TierLedger()
    tool_fn = make_notify_parties(repo, sink, tier_ledger)
    return tool_fn, repo, sink, tier_ledger


def test_green_action_sends_without_approval_token():
    tool_fn, _, sink, tier_ledger = _build()
    tier_ledger.record("room_conflict:b_oneoff_a:b_recurring_a", Tier.GREEN, Workflow.ROOM_BOOKING)
    result = tool_fn(library_id="lib_demo", related_action_id="room_conflict:b_oneoff_a:b_recurring_a", subject="Booking update", body="Your booking has changed.")
    body = result["content"][0]["json"]
    assert body["status"] == "sent"
    assert len(sink.all()) == 1
    assert set(sink.all()[0]["recipients"]) == {"patron_recurring", "patron_renter"}


def test_yellow_action_requires_valid_approval_token():
    tool_fn, _, _, tier_ledger = _build()
    tier_ledger.record("ill_request:ill_ambiguous", Tier.YELLOW, Workflow.ILL_ROUTING)
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
    tier_ledger.record("overdue:circ_green", Tier.GREEN, Workflow.OVERDUE_CHASE)
    result = tool_fn(library_id="lib_demo", related_action_id="overdue:circ_green", subject="Reminder", body="Please provide your Social Security Number to confirm.")
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_by_guardrail"
    assert body["guardrail_findings"]
    assert sink.all() == []
