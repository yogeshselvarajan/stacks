"""search_ill_catalog_candidates -- the ILL Disambiguation Specialist's own,
private, deterministic catalog search. Never exposed to the top-level
Stacks Agent's tool list. See docs/architecture/tool_architecture.md
section 3.9.
"""
from __future__ import annotations

from typing import Any

from strands import tool

from stacks.data.repository import LibraryDataRepository


def make_search_ill_catalog_candidates(repo: LibraryDataRepository, session_library_id: str):
    @tool
    def search_ill_catalog_candidates(
        library_id: str,
        ill_request_id: str,
        search_terms: list[str],
        within_candidate_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deterministic catalog-metadata search scoped to one ILL request's
        own candidate space. Narrows, never expands, the search space.

        Args:
            library_id: Tenant scope; must match the session's own library_id.
            ill_request_id: Scopes the search to this case's own candidate space.
            search_terms: Refined terms the specialist composes each turn.
            within_candidate_ids: Optionally narrows to a subset of the
                original candidates. Must be a subset of the case's own
                candidate_matches -- this tool cannot surface a holding
                outside that set.

        Returns:
            {"matches": [...CatalogCandidate...], "exhausted": bool}
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        request = repo.get_ill_request(library_id, ill_request_id)
        if request is None:
            return {"status": "error", "content": [{"text": "not_found: no ILL request with that id"}]}

        candidates = repo.search_catalog_candidates(library_id, request.requested_title, request.requested_edition_hint)

        if within_candidate_ids is not None:
            valid_ids = {c.holding_id for c in candidates}
            if not set(within_candidate_ids).issubset(valid_ids):
                return {"status": "error", "content": [{"text": "invalid_narrowing: within_candidate_ids must be a subset of this case's own candidates"}]}
            candidates = [c for c in candidates if c.holding_id in within_candidate_ids]

        return {"status": "success", "content": [{"json": {
            "matches": [c.model_dump(mode="json") for c in candidates],
            "exhausted": len(candidates) <= 1,
        }}]}

    return search_ill_catalog_candidates
