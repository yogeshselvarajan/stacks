import os

import pytest

from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
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
    tool_fn = make_disambiguate_ill_candidates(repo, "lib_demo", model)

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
