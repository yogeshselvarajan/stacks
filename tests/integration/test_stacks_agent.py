import os

import pytest

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.agent import build_stacks_agent


def _build_bundle():
    # build_stacks_agent fails closed if STACKS_BEDROCK_MODEL_ID is unset
    # (final_architecture.md section 4.2: the model ID is never hardcoded).
    # The two offline tests below only construct the Agent and inspect its
    # tool/hook registries -- they never invoke it -- so a syntactically
    # plausible placeholder is sufficient and is only injected when we are
    # NOT in a live-Bedrock run, so a real live run still fails loudly if
    # the operator forgot to set the real model ID themselves.
    if not os.environ.get("RUN_LIVE_BEDROCK_TESTS"):
        os.environ.setdefault("STACKS_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return build_stacks_agent(repo, library_id="lib_demo", session_id="sess_test")


def test_build_stacks_agent_registers_all_five_plan_1_tools():
    bundle = _build_bundle()
    tool_names = {t.tool_name for t in bundle.agent.tool_registry.registry.values()}
    assert tool_names == {"get_library_data", "resolve_room_conflict", "route_ill_request", "run_overdue_chase", "notify_parties"}


def test_build_stacks_agent_registers_both_hooks():
    from stacks.hitl.hitl_gate import HitlGateHook
    from stacks.hooks.audit_log import AuditLogHook
    from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent

    bundle = _build_bundle()
    registry = bundle.agent.hooks
    before_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(BeforeToolCallEvent, [])}
    after_owners = {cb.__self__.__class__ for cb in registry._registered_callbacks.get(AfterToolCallEvent, [])}
    assert HitlGateHook in before_owners
    assert AuditLogHook in after_owners


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_BEDROCK_TESTS"),
    reason="Requires real AWS credentials and Bedrock model access. Set RUN_LIVE_BEDROCK_TESTS=1 to run.",
)
def test_green_room_booking_conflict_resolves_end_to_end_via_real_bedrock():
    """The one test in this plan that makes a real Bedrock call. Exercises
    the full Agent + HitlGateHook + AuditLogHook wiring together, per this
    plan's Global Constraints note that only this test is allowed to touch
    AWS.
    """
    bundle = _build_bundle()
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
def test_red_room_booking_conflict_interrupts_and_resumes_via_real_bedrock():
    bundle = _build_bundle()
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
