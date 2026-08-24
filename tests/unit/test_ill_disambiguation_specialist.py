import os
from unittest.mock import MagicMock, patch

import pytest

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.tools.disambiguate_ill_candidates import ILLDisambiguationResult, make_disambiguate_ill_candidates


def _repo():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return repo


def test_result_model_rejects_a_narrowed_candidate_id_outside_the_input_set():
    # This is the wrapper boundary's own closed-world check, exercised
    # directly against the wrapper function's validation logic, not
    # against a real Bedrock call.
    from stacks.tools.disambiguate_ill_candidates import _validate_narrowed_candidate

    with pytest.raises(ValueError):
        _validate_narrowed_candidate("hold_not_in_set", candidate_ids={"hold_2a", "hold_2b"})

    _validate_narrowed_candidate("hold_2a", candidate_ids={"hold_2a", "hold_2b"})  # does not raise


def test_result_model_allows_none_when_still_ambiguous():
    result = ILLDisambiguationResult(narrowed_candidate_id=None, confidence=0.0, still_ambiguous=True)
    assert result.still_ambiguous is True


def test_live_specialist_converges_on_an_unambiguous_narrowing_prompt():
    model_id = os.environ.get("STACKS_BEDROCK_MODEL_ID")
    if not model_id:
        pytest.skip("STACKS_BEDROCK_MODEL_ID not set -- live Bedrock smoke test, skipped by default")

    from strands.models import BedrockModel

    repo = _repo()
    model = BedrockModel(model_id=model_id, region_name=os.environ.get("STACKS_AWS_REGION", "us-west-2"), temperature=0.0)
    tool_fn = make_disambiguate_ill_candidates(repo, "lib_demo", model, EvaluationCache())

    result = tool_fn(
        library_id="lib_demo",
        ill_request_id="ill_ambiguous",
        candidate_matches=[
            {"holding_id": "hold_2a", "edition": "Penguin Classics", "location": "lib_partner_a", "availability": "available"},
            {"holding_id": "hold_2b", "edition": "Oxford World's Classics", "location": "lib_partner_b", "availability": "unavailable"},
        ],
        requester_pattern=None,
    )
    body = result["content"][0]["json"]
    if not body["still_ambiguous"]:
        assert body["narrowed_candidate_id"] in ("hold_2a", "hold_2b")


def test_disambiguate_ill_candidates_writes_result_into_disambiguation_cache():
    """Whole-branch review Critical 1: a successful specialist run must
    write its own result into disambiguation_cache, keyed
    (library_id, ill_request_id) -- this is the code-held record
    route_ill_request's commit path and HitlGateHook later verify a
    resolved_via_substitution claim against. Mocks strands.Agent so this
    runs offline, no AWS credentials needed."""
    repo = _repo()
    disambiguation_cache = EvaluationCache()
    fake_specialist = MagicMock()
    fake_specialist.structured_output.return_value = ILLDisambiguationResult(
        narrowed_candidate_id="hold_2a", confidence=0.95, still_ambiguous=False,
    )

    with patch("stacks.tools.disambiguate_ill_candidates.Agent", return_value=fake_specialist):
        tool_fn = make_disambiguate_ill_candidates(repo, "lib_demo", model=object(), disambiguation_cache=disambiguation_cache)
        result = tool_fn(
            library_id="lib_demo",
            ill_request_id="ill_req_cache_test",
            candidate_matches=[
                {"holding_id": "hold_2a", "edition": "Penguin Classics", "location": "lib_partner_a", "availability": "available"},
            ],
            requester_pattern=None,
        )

    assert result["status"] == "success"
    assert result["content"][0]["json"]["narrowed_candidate_id"] == "hold_2a"

    cached = disambiguation_cache.get("lib_demo", "ill_req_cache_test")
    assert cached is not None
    assert cached["narrowed_candidate_id"] == "hold_2a"
    assert cached["confidence"] == 0.95
    assert cached["still_ambiguous"] is False


def test_disambiguate_ill_candidates_does_not_write_cache_on_invocation_failure():
    """A failed specialist invocation has no real result to record -- the
    cache must stay empty for this case, not contain a fabricated entry."""
    repo = _repo()
    disambiguation_cache = EvaluationCache()
    fake_specialist = MagicMock()
    fake_specialist.structured_output.side_effect = RuntimeError("simulated specialist failure")

    with patch("stacks.tools.disambiguate_ill_candidates.Agent", return_value=fake_specialist):
        tool_fn = make_disambiguate_ill_candidates(repo, "lib_demo", model=object(), disambiguation_cache=disambiguation_cache)
        result = tool_fn(
            library_id="lib_demo",
            ill_request_id="ill_req_fail_test",
            candidate_matches=[
                {"holding_id": "hold_2a", "edition": "Penguin Classics", "location": "lib_partner_a", "availability": "available"},
            ],
            requester_pattern=None,
        )

    assert result["status"] == "error"
    assert disambiguation_cache.get("lib_demo", "ill_req_fail_test") is None


def test_disambiguate_ill_candidates_writes_forced_still_ambiguous_result_on_out_of_set_candidate():
    """When the specialist returns a candidate outside the case's own set,
    the wrapper forces still_ambiguous=True before returning -- and it is
    this forced, safe result that gets cached, not the specialist's
    original out-of-bounds claim."""
    repo = _repo()
    disambiguation_cache = EvaluationCache()
    fake_specialist = MagicMock()
    fake_specialist.structured_output.return_value = ILLDisambiguationResult(
        narrowed_candidate_id="hold_not_in_set", confidence=0.99, still_ambiguous=False,
    )

    with patch("stacks.tools.disambiguate_ill_candidates.Agent", return_value=fake_specialist):
        tool_fn = make_disambiguate_ill_candidates(repo, "lib_demo", model=object(), disambiguation_cache=disambiguation_cache)
        tool_fn(
            library_id="lib_demo",
            ill_request_id="ill_req_out_of_set",
            candidate_matches=[
                {"holding_id": "hold_2a", "edition": "Penguin Classics", "location": "lib_partner_a", "availability": "available"},
            ],
            requester_pattern=None,
        )

    cached = disambiguation_cache.get("lib_demo", "ill_req_out_of_set")
    assert cached is not None
    assert cached["narrowed_candidate_id"] is None
    assert cached["still_ambiguous"] is True
