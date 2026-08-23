from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.tools.route_ill_request import make_route_ill_request


def _build():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_route_ill_request(repo, cache, tier_ledger, "lib_demo")
    return tool_fn, repo, tier_ledger


def test_evaluate_unambiguous_request():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    body = result["content"][0]["json"]
    assert body["ambiguity"] == "none"
    assert body["requester_pattern"] is None
    assert len(body["candidate_matches"]) == 1


def test_evaluate_ambiguous_request():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    body = result["content"][0]["json"]
    assert body["ambiguity"] == "multiple_editions"
    assert len(body["candidate_matches"]) == 2


def test_commit_unambiguous_request_is_green_no_approval_needed():
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit", chosen_holding_id="hold_1", rationale="Matches per ILL-1.")
    body = result["content"][0]["json"]
    assert body["status"] == "committed"
    assert repo.get_ill_request("lib_demo", "ill_unambiguous").status.value == "routed"
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("lib_demo", "ill_request:ill_unambiguous") == (Tier.GREEN, Workflow.ILL_ROUTING)


def test_commit_ambiguous_request_blocked_without_approval():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit", chosen_holding_id="hold_2a", rationale="Nearest partner per ILL-1.")
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_commit_ambiguous_request_succeeds_with_coordinator_approval():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit", chosen_holding_id="hold_2a", rationale="Nearest partner per ILL-1.",
        approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_ambiguous"},
    )
    assert result["content"][0]["json"]["status"] == "committed"


def test_commit_choice_outside_candidate_set_is_rejected():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit", chosen_holding_id="hold_does_not_exist", rationale="Matches per ILL-1.")
    assert result["content"][0]["json"]["status"] == "blocked_invalid_choice"


def test_already_routed_request_cannot_be_re_evaluated():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit", chosen_holding_id="hold_1", rationale="Matches per ILL-1.")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    assert result["status"] == "error"
    assert "already_routed" in result["content"][0]["text"]
