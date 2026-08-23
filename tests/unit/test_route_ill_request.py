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


def test_cross_tenant_denial():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_other", ill_request_id="ill_unambiguous", action="evaluate")
    assert result["status"] == "error"
    assert result["content"][0]["text"] == "cross_tenant_denied"


def test_not_found_nonexistent_ill_request():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_does_not_exist", action="evaluate")
    assert result["status"] == "error"
    assert "not_found" in result["content"][0]["text"]


def test_invalid_action():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="invalid")
    assert result["status"] == "error"
    assert "invalid_action" in result["content"][0]["text"]


def test_evaluate_not_called():
    tool_fn, _, _ = _build()
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit", chosen_holding_id="hold_1", rationale="Matches per ILL-1.")
    assert result["status"] == "error"
    assert "evaluate_not_called" in result["content"][0]["text"]


def test_no_match_recorded_path():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit", chosen_holding_id=None, rationale="No match per ILL-1 review.", approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_ambiguous"})
    assert result["content"][0]["json"]["status"] == "no_match_recorded"


def test_policy_exception_red_flag_requires_approval():
    from stacks.data.models import ILLRequestRecord
    from stacks.types import SensitivityFlag
    tool_fn, repo, _ = _build()
    # Create a flagged request
    flagged_request = ILLRequestRecord(
        ill_request_id="ill_flagged", library_id="lib_demo",
        requested_title="The Structure of Scientific Revolutions",
        requester_patron_id="patron_ill_flagged",
        flags=[SensitivityFlag.POLICY_EXCEPTION_REQUIRED],
    )
    repo.save_ill_request(flagged_request)
    # Evaluate should show policy_exception ambiguity
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_flagged", action="evaluate")
    body = result["content"][0]["json"]
    assert body["ambiguity"] == "policy_exception"
    # Commit without approval should be blocked (even with proper rationale)
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_flagged", action="commit", chosen_holding_id=None, rationale="Policy exception per ILL-1.")
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_malformed_approval_token_treated_as_none():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    # Malformed token (missing required field) should not crash
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit", chosen_holding_id="hold_1", rationale="Matches per ILL-1.", approval_token={"invalid": "token"})
    # Should succeed because the unambiguous case is GREEN (no approval needed) and malformed token is ignored
    assert result["content"][0]["json"]["status"] == "committed"


def test_mismatched_approval_token_related_action_id_rejected():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    # Token with different related_action_id
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit", chosen_holding_id="hold_2a", rationale="Nearest partner per ILL-1.", approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_different"})
    assert result["content"][0]["json"]["status"] == "blocked_missing_approval"


def test_rationale_missing_clause_id_citation_rejected():
    tool_fn, _, _ = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    # Rationale missing the clause_id "ILL-1"
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit", chosen_holding_id="hold_2a", rationale="Some other reason.", approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_ambiguous"})
    assert result["content"][0]["json"]["status"] == "blocked_invalid_choice"


def test_cross_tenant_catalog_isolation():
    """Seeds two libraries with colliding book titles and different holdings,
    then asserts that library A's evaluate only sees library A's holdings."""
    from stacks.data.models import CatalogCandidate, ILLRequestRecord

    repo = InMemoryLibraryDataRepository()

    # Seed lib_a with title "Shared Title" and holding hold_a
    repo.set_catalog_candidates("lib_a", "Shared Title", [
        CatalogCandidate(holding_id="hold_a", edition="1st", location="lib_a_partner", availability="available"),
    ])

    # Seed lib_b with same title "Shared Title" but different holding hold_b
    repo.set_catalog_candidates("lib_b", "Shared Title", [
        CatalogCandidate(holding_id="hold_b", edition="2nd", location="lib_b_partner", availability="available"),
    ])

    # Create ILL request in lib_a
    repo.save_ill_request(ILLRequestRecord(
        ill_request_id="ill_shared_a", library_id="lib_a",
        requested_title="Shared Title", requester_patron_id="patron_a",
    ))

    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn_a = make_route_ill_request(repo, cache, tier_ledger, "lib_a")

    # Evaluate lib_a's request — should only see hold_a
    result = tool_fn_a(library_id="lib_a", ill_request_id="ill_shared_a", action="evaluate")
    candidates = result["content"][0]["json"]["candidate_matches"]
    holding_ids = [c["holding_id"] for c in candidates]
    assert holding_ids == ["hold_a"], f"Expected ['hold_a'] but got {holding_ids}"
