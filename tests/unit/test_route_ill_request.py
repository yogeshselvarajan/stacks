from datetime import datetime, timezone

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.hitl.tier_ledger import TierLedger
from stacks.memory.store import InMemoryMemoryStore
from stacks.tools.route_ill_request import make_route_ill_request
from stacks.types import RequesterSubstitutionPattern


def _repo():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return repo


def _build():
    repo = _repo()
    cache = EvaluationCache()
    tier_ledger = TierLedger()
    tool_fn = make_route_ill_request(repo, cache, tier_ledger, "lib_demo", InMemoryMemoryStore())
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
    """Test that a flagged request with NO catalog candidates returns
    policy_exception ambiguity (not no_match), verifying the flag check
    happens before the no-candidates check."""
    from stacks.data.models import ILLRequestRecord
    from stacks.types import SensitivityFlag
    tool_fn, repo, _ = _build()
    # Create a flagged request for a title NOT in the catalog
    flagged_request = ILLRequestRecord(
        ill_request_id="ill_flagged_no_candidates", library_id="lib_demo",
        requested_title="Rare Untitled Manuscript 1923",
        requester_patron_id="patron_ill_flagged",
        flags=[SensitivityFlag.POLICY_EXCEPTION_REQUIRED],
    )
    repo.save_ill_request(flagged_request)
    # Evaluate should show policy_exception ambiguity (not no_match)
    # This is the crucial test: the flag check must come before the no-candidates check
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_flagged_no_candidates", action="evaluate")
    body = result["content"][0]["json"]
    assert body["ambiguity"] == "policy_exception", f"Expected policy_exception but got {body['ambiguity']}"
    # Commit without approval should be blocked (even with proper rationale)
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_flagged_no_candidates", action="commit", chosen_holding_id=None, rationale="Policy exception per ILL-1.")
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
    tool_fn_a = make_route_ill_request(repo, cache, tier_ledger, "lib_a", InMemoryMemoryStore())

    # Evaluate lib_a's request, it should only see hold_a
    result = tool_fn_a(library_id="lib_a", ill_request_id="ill_shared_a", action="evaluate")
    candidates = result["content"][0]["json"]["candidate_matches"]
    holding_ids = [c["holding_id"] for c in candidates]
    assert holding_ids == ["hold_a"], f"Expected ['hold_a'] but got {holding_ids}"


def test_evaluate_returns_recalled_requester_pattern_when_present():
    repo = _repo()  # reuse this file's existing fixture helper
    memory = InMemoryMemoryStore()
    memory.set_ill_substitution_pattern("lib_demo", "patron_ill_2", RequesterSubstitutionPattern(
        request_frequency=2, subject_areas=["fiction"],
        has_accepted_substitution_without_escalation=True,
        last_updated=datetime(2026, 7, 1, tzinfo=timezone.utc),
    ))
    tool_fn = make_route_ill_request(repo, EvaluationCache(), TierLedger(), "lib_demo", memory)

    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    body = result["content"][0]["json"]
    assert body["requester_pattern"]["has_accepted_substitution_without_escalation"] is True


def test_evaluate_fails_open_on_memory_retrieval_error():
    repo = _repo()

    class RaisingMemory:
        def get_ill_substitution_pattern(self, library_id, requester_key):
            raise RuntimeError("simulated retrieval failure")

    tool_fn = make_route_ill_request(repo, EvaluationCache(), TierLedger(), "lib_demo", RaisingMemory())
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    assert result["status"] == "success"
    assert result["content"][0]["json"]["requester_pattern"] is None


def test_commit_with_resolved_via_substitution_true_is_green_without_approval_token():
    tool_fn, _, tier_ledger = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit",
        chosen_holding_id="hold_2a", rationale="Per ILL-1, specialist converged on Penguin Classics edition.",
        resolved_via_substitution=True,
    )
    body = result["content"][0]["json"]
    assert body["status"] == "committed"
    assert body["resolved_via_substitution"] is True
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("lib_demo", "ill_request:ill_ambiguous") == (Tier.GREEN, Workflow.ILL_ROUTING)


def test_commit_no_holding_with_resolved_via_substitution_true_is_blocked_not_green():
    """resolved_via_substitution is definitionally a claim about having
    converged on a specific holding -- a commit with chosen_holding_id=None
    (a no-match outcome) can never honestly be "resolved", regardless of
    the caller's flag. Without this guard, this call would classify GREEN
    and close the request as NO_MATCH with no approval token and no human
    ever asked (reviewer-confirmed bypass on Task 11)."""
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit",
        chosen_holding_id=None, rationale="No confident match per ILL-1.",
        resolved_via_substitution=True,
    )
    body = result["content"][0]["json"]
    assert body["status"] == "blocked_missing_approval"
    assert body["resolved_via_substitution"] is False
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("lib_demo", "ill_request:ill_ambiguous") is None
    assert repo.get_ill_request("lib_demo", "ill_ambiguous").status.value == "open"


def test_commit_no_holding_with_resolved_via_substitution_true_succeeds_with_yellow_approval():
    """The same no-holding + resolved_via_substitution=True call, but with
    a valid YELLOW-tier approval token, commits as no_match_recorded --
    confirming the effective tier is YELLOW (not RED, not an unreachable
    GREEN-that-was-actually-blocked), and that the returned
    resolved_via_substitution honestly reports False since nothing was
    actually substituted."""
    tool_fn, repo, tier_ledger = _build()
    tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", action="commit",
        chosen_holding_id=None, rationale="No confident match per ILL-1.",
        resolved_via_substitution=True,
        approval_token={"token": "t", "approver_role": "ill_coordinator", "related_action_id": "ill_request:ill_ambiguous"},
    )
    body = result["content"][0]["json"]
    assert body["status"] == "no_match_recorded"
    assert body["resolved_via_substitution"] is False
    from stacks.hitl.classify import Tier, Workflow
    assert tier_ledger.get("lib_demo", "ill_request:ill_ambiguous") == (Tier.YELLOW, Workflow.ILL_ROUTING)
    assert repo.get_ill_request("lib_demo", "ill_ambiguous").status.value == "no_match"


def test_committed_result_carries_requester_patron_id_and_subject_area_for_memory_hook():
    repo = _repo()
    memory = InMemoryMemoryStore()
    tool_fn = make_route_ill_request(repo, EvaluationCache(), TierLedger(), "lib_demo", memory)
    tool_fn(library_id="lib_demo", ill_request_id="ill_unambiguous", action="evaluate")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_unambiguous", action="commit",
        chosen_holding_id="hold_1", rationale="Per ILL-1, single available match.",
    )
    body = result["content"][0]["json"]
    assert body["requester_patron_id"] == "patron_ill_1"
