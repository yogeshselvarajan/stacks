import os
from datetime import datetime, timezone

import pytest

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.agent import build_stacks_agent
from stacks.identity.claims import StaffIdentityClaims


def _build_bundle(monkeypatch):
    # build_stacks_agent fails closed if STACKS_BEDROCK_MODEL_ID is unset
    # (final_architecture.md section 4.2: the model ID is never hardcoded).
    # The two offline tests below only construct the Agent and inspect its
    # tool/hook registries -- they never invoke it -- so a syntactically
    # plausible placeholder is sufficient and is only injected when we are
    # NOT in a live-Bedrock run, so a real live run still fails loudly if
    # the operator forgot to set the real model ID themselves. Uses
    # monkeypatch (not a bare os.environ.setdefault) so the placeholder is
    # automatically un-set at the end of *this* test -- a bare setdefault
    # with no cleanup previously leaked STACKS_BEDROCK_MODEL_ID into every
    # later test in a full-suite run, wrongly "activating" other tests'
    # opt-in live-Bedrock smoke tests that gate on that same env var
    # (found while implementing Task 10 of Plan 2).
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    return build_stacks_agent(repo, claims, session_id="sess_test")


def test_build_stacks_agent_derives_library_id_from_claims(monkeypatch):
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    claims = StaffIdentityClaims(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")

    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS") and not os.environ.get("STACKS_BEDROCK_MODEL_ID"):
        monkeypatch.setenv("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    bundle = build_stacks_agent(repo, claims, session_id="sess_1", now=lambda: datetime(2026, 9, 5, tzinfo=timezone.utc))

    # get_library_data is scoped internally to session_library_id, derived
    # from claims.library_id. A query naming the same tenant string
    # ("lib_demo") must succeed -- if build_stacks_agent forgot to unwrap
    # claims.library_id and instead closed the tool over the whole claims
    # object, this same query would come back cross_tenant_denied because
    # "lib_demo" != <StaffIdentityClaims instance>.
    get_library_data_tool = bundle.agent.tool_registry.registry["get_library_data"]
    result = get_library_data_tool(
        library_id="lib_demo",
        query_type="room_calendar",
        room_calendar_filter={
            "room_id": "room_a",
            "start": "2026-09-01T00:00:00+00:00",
            "end": "2026-09-02T00:00:00+00:00",
        },
    )
    assert result["status"] == "success"


def test_build_stacks_agent_registers_all_six_tools(monkeypatch):
    bundle = _build_bundle(monkeypatch)
    tool_names = {t.tool_name for t in bundle.agent.tool_registry.registry.values()}
    assert tool_names == {
        "get_library_data",
        "resolve_room_conflict",
        "route_ill_request",
        "run_overdue_chase",
        "notify_parties",
        "disambiguate_ill_candidates",
    }


def test_build_stacks_agent_registers_both_hooks(monkeypatch):
    from stacks.hitl.hitl_gate import HitlGateHook
    from stacks.hooks.audit_log import AuditLogHook
    from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent

    bundle = _build_bundle(monkeypatch)
    registry = bundle.agent.hooks
    before_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(BeforeToolCallEvent, [])}
    after_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(AfterToolCallEvent, [])}
    assert HitlGateHook in before_owners
    assert AuditLogHook in after_owners


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_green_room_booking_conflict_resolves_end_to_end_via_real_bedrock(monkeypatch):
    """The one test in this plan that makes a real Bedrock call. Exercises
    the full Agent + HitlGateHook + AuditLogHook wiring together, per this
    plan's Global Constraints note that only this test is allowed to touch
    AWS.
    """
    bundle = _build_bundle(monkeypatch)
    result = bundle.agent(
        "There is a room-booking conflict between booking b_recurring_a and "
        "booking b_oneoff_a in room_a. Resolve it per the room booking "
        "priority policy and notify both parties."
    )
    assert result.stop_reason != "interrupt"
    audit_records = bundle.audit_sink.all()
    assert any(r.tool_name == "resolve_room_conflict" and r.tool_output_status == "success" for r in audit_records)
    assert len(bundle.notification_sink.all()) >= 1


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_red_room_booking_conflict_interrupts_and_resumes_via_real_bedrock(monkeypatch):
    bundle = _build_bundle(monkeypatch)
    result = bundle.agent(
        "There is a room-booking conflict between booking b_recurring_b and "
        "booking b_walkin_b in room_b. Evaluate it and attempt to resolve "
        "it per the room booking priority policy."
    )
    assert result.stop_reason == "interrupt"
    assert len(result.interrupts) == 1

    responses = [{"interruptResponse": {"interruptId": result.interrupts[0].id, "response": None}}]
    bundle.agent(responses)
    # A None response (no approval_token supplied) must not silently commit --
    # cross-check against the audit trail's outcome field (the true
    # committed/blocked_missing_approval/already_committed/blocked_invalid_choice
    # outcome from the tool's own nested result, extracted by AuditLogHook's
    # _extract_outcome), not the envelope tool_output_status (which is
    # "success" for both a real commit and a blocked-but-well-formed
    # response) and not a substring check against tool_input (which only
    # ever contains the action name "commit", never the outcome string
    # "committed").
    audit_records = bundle.audit_sink.all()
    committed = [r for r in audit_records if r.tool_name == "resolve_room_conflict" and r.outcome == "committed"]
    assert committed == []
