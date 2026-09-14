"""disambiguate_ill_candidates -- the Agents-as-Tools wrapper invoking the
ILL Disambiguation Specialist. See docs/architecture/agent_architecture.md
section 2 and tool_architecture.md section 3.8.

Per this plan's SDK-verification note: strands-agents 1.32.0 has no
Agent.as_tool() method. This wrapper is a plain @tool-decorated function
that constructs and invokes a second Agent instance directly -- the real,
verified "Agents as Tools" pattern for this SDK version.

Turn-budget note (implementer verification, 2026-08-24): direct
inspection of the installed strands-agents 1.32.0 package
(inspect.signature(Agent.__init__)) confirms Agent has no max-turns /
max-iterations / max-invocations constructor argument. A further search
of strands.event_loop for a recursion or invocation-count cap (grep for
"recursion", "max_iterations", "tool_use_count", etc. across the
installed package) found none either -- the only bounded-retry constant
present (MAX_ATTEMPTS in strands/event_loop/event_loop.py) governs model
*throttling* retries, not tool-calling turns. In this SDK version, an
Agent's tool-calling loop is bounded by the model itself choosing to stop
requesting tool use (a stop_reason other than a tool-use request), not by
an SDK-enforced hard cap. This is the same mechanism the top-level Stacks
Agent already relies on per Plan 1's Global Constraints ("runaway
tool-calling is bounded by Strands invocation limits") -- so the
specialist Agent constructed below is bound by exactly the same
mechanism as the top-level agent, no better and no worse. _MAX_SPECIALIST_TURNS
is kept as a documented intent constant (and named in the system prompt)
rather than a constructor argument, since the SDK offers no such argument
to pass it to.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from strands import Agent, tool

from stacks.data.repository import LibraryDataRepository
from stacks.hitl.evaluation_cache import EvaluationCache
from stacks.tools.get_library_data import make_get_library_data
from stacks.tools.search_ill_catalog_candidates import make_search_ill_catalog_candidates

_SPECIALIST_SYSTEM_PROMPT = """You are the ILL Disambiguation Specialist. \
Given a set of candidate catalog matches for an interlibrary-loan request, \
and optionally a recalled requester substitution pattern, narrow to a \
single confident candidate or conclude no confident match exists.

Use search_ill_catalog_candidates to refine your search within the given \
candidate set only -- you may never surface a holding outside the \
candidate_matches you were given. A recalled requester pattern may raise \
or lower your confidence in a candidate the catalog data already \
supports; it must never cause you to select a candidate the catalog data \
does not support. Stop and report still_ambiguous=True once you have \
tried a reasonable number of refinements (at most a handful of turns) \
without reaching a single confident candidate -- do not loop indefinitely."""

_MAX_SPECIALIST_TURNS = 4


class ILLDisambiguationResult(BaseModel):
    narrowed_candidate_id: str | None
    confidence: float
    still_ambiguous: bool


def _validate_narrowed_candidate(candidate_id: str | None, candidate_ids: set[str]) -> None:
    if candidate_id is not None and candidate_id not in candidate_ids:
        raise ValueError(f"specialist returned a candidate outside the case's own set: {candidate_id!r}")


def make_disambiguate_ill_candidates(
    repo: LibraryDataRepository,
    session_library_id: str,
    model,
    disambiguation_cache: EvaluationCache,
):
    @tool
    def disambiguate_ill_candidates(
        library_id: str,
        ill_request_id: str,
        candidate_matches: list[dict[str, Any]],
        requester_pattern: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Invoke the ILL Disambiguation Specialist to narrow an ambiguous
        set of candidate catalog matches to a single confident candidate,
        or a definitive no-confident-match state. Never itself HITL-gated
        -- no commit/send semantics, no approval_token field.

        On success, writes its own result into disambiguation_cache keyed
        (library_id, ill_request_id) -- this is the code-held record that
        route_ill_request's commit path and HitlGateHook later verify a
        resolved_via_substitution claim against, rather than trusting the
        model-supplied flag alone (stacks.hitl.ill_disambiguation_verification,
        whole-branch review Critical 1). A failed invocation writes nothing,
        since no real result exists to record.

        Args:
            library_id: Tenant scope; must match the session's own library_id.
            ill_request_id: The ILL request being narrowed.
            candidate_matches: Verbatim from route_ill_request's evaluate output.
            requester_pattern: Verbatim from the same evaluate output, or None.

        Returns:
            {"narrowed_candidate_id": str|None, "confidence": float, "still_ambiguous": bool}
        """
        if library_id != session_library_id:
            return {"status": "error", "content": [{"text": "cross_tenant_denied"}]}

        candidate_ids = {c["holding_id"] for c in candidate_matches}

        specialist_tools = [
            make_get_library_data(repo, session_library_id),
            make_search_ill_catalog_candidates(repo, session_library_id),
        ]
        specialist = Agent(
            model=model,
            tools=specialist_tools,
            system_prompt=_SPECIALIST_SYSTEM_PROMPT,
        )

        prompt = (
            f"ill_request_id: {ill_request_id}\n"
            f"library_id: {library_id}\n"
            f"candidate_matches: {candidate_matches}\n"
            f"requester_pattern: {requester_pattern}\n"
            f"Narrow to one confident candidate or report still_ambiguous."
        )

        try:
            result = specialist.structured_output(ILLDisambiguationResult, prompt)
        except Exception as exc:
            return {"status": "error", "content": [{"text": f"specialist_invocation_failed: {exc}"}]}

        try:
            _validate_narrowed_candidate(result.narrowed_candidate_id, candidate_ids)
        except ValueError:
            result = ILLDisambiguationResult(narrowed_candidate_id=None, confidence=0.0, still_ambiguous=True)

        disambiguation_cache.put(library_id, ill_request_id, result.model_dump(mode="json"))

        # Also persist onto the request's own durable record (unlike the
        # cache above, this survives past this process) so the BFF's read
        # endpoint -- a SEPARATE process, invoked long after this agent
        # invocation ends -- can show the specialist's trace at all.
        request = repo.get_ill_request(library_id, ill_request_id)
        if request is not None:
            request.specialist_narrowed_candidate_id = result.narrowed_candidate_id
            request.specialist_confidence = result.confidence
            request.specialist_still_ambiguous = result.still_ambiguous
            repo.save_ill_request(request)

        return {"status": "success", "content": [{"json": result.model_dump(mode="json")}]}

    return disambiguate_ill_candidates
