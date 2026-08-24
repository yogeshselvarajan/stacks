from stacks.data.fixtures import seed_demo_library
from stacks.data.memory_repository import InMemoryLibraryDataRepository
from stacks.tools.search_ill_catalog_candidates import make_search_ill_catalog_candidates


def _repo():
    repo = InMemoryLibraryDataRepository()
    seed_demo_library(repo, library_id="lib_demo")
    return repo


def test_search_returns_matches_for_the_case_title():
    tool_fn = make_search_ill_catalog_candidates(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", ill_request_id="ill_ambiguous", search_terms=["Middlemarch"], within_candidate_ids=None)
    assert result["status"] == "success"
    matches = result["content"][0]["json"]["matches"]
    assert len(matches) == 2


def test_within_candidate_ids_narrows_the_result_to_a_subset():
    tool_fn = make_search_ill_catalog_candidates(_repo(), "lib_demo")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", search_terms=["Middlemarch"],
        within_candidate_ids=["hold_2a"],
    )
    matches = result["content"][0]["json"]["matches"]
    assert [m["holding_id"] for m in matches] == ["hold_2a"]


def test_within_candidate_ids_outside_the_case_original_candidates_is_rejected():
    tool_fn = make_search_ill_catalog_candidates(_repo(), "lib_demo")
    result = tool_fn(
        library_id="lib_demo", ill_request_id="ill_ambiguous", search_terms=["Middlemarch"],
        within_candidate_ids=["hold_not_a_real_candidate"],
    )
    assert result["status"] == "error"
    assert "invalid_narrowing" in result["content"][0]["text"]


def test_cross_tenant_query_is_denied():
    tool_fn = make_search_ill_catalog_candidates(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_other", ill_request_id="ill_ambiguous", search_terms=[], within_candidate_ids=None)
    assert result["status"] == "error"
    assert "cross_tenant_denied" in result["content"][0]["text"]


def test_unknown_ill_request_id_returns_not_found():
    tool_fn = make_search_ill_catalog_candidates(_repo(), "lib_demo")
    result = tool_fn(library_id="lib_demo", ill_request_id="does_not_exist", search_terms=[], within_candidate_ids=None)
    assert result["status"] == "error"
    assert "not_found" in result["content"][0]["text"]
