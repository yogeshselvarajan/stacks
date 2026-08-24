"""Shared reduction that verifies a route_ill_request commit's
resolved_via_substitution claim against the ILL Disambiguation
Specialist's own cached convergence result, so a model-supplied claim
alone can never satisfy classify_ill_routing's resolved_via_substitution
input.

Whole-branch review Critical 1: before this module existed,
resolved_via_substitution was a model-supplied boolean with nothing
verifying the ILL Disambiguation Specialist ever ran. An ambiguous ILL
request (ambiguity="multiple_editions") could be committed with
resolved_via_substitution=True and a chosen holding id, auto-routing at
GREEN with no human approval and no call to disambiguate_ill_candidates
ever having happened -- the model simply asserted the flag.

docs/architecture/agent_architecture.md section 4.4 and section 5.3 both
require that the specialist's output refine the *existing* ambiguity
input classify() already reads, and that Memory/specialist facts must
never feed classify() directly as a new, unverified input. This module is
that refinement step: it reduces a cache lookup to a plain bool, which is
the only thing classify_ill_routing (stacks.hitl.classify) is ever handed
-- classify() itself never sees the cache, the tool_input, or the
specialist's raw output.

Used identically by route_ill_request.py's own commit-path classification
and hitl_gate.py's _classify_from_evaluation -- both call this same
function so the tool and the gate can never disagree about the tier.

The cache itself is a plain stacks.hitl.evaluation_cache.EvaluationCache
instance (keyed (library_id, ill_request_id) -> dict), constructed once in
agent.py and shared between disambiguate_ill_candidates (which writes to
it) and route_ill_request/HitlGateHook (which read from it) -- the same
sharing pattern the three existing EvaluationCache instances already use.
No new cache class was invented; EvaluationCache's shape already fits.
"""
from __future__ import annotations

from stacks.hitl.evaluation_cache import EvaluationCache

# Confidence floor below which a specialist convergence is not trusted to
# auto-route at GREEN, even when still_ambiguous is False. Named here, not
# inline, so this one file is where the threshold is tuned.
MIN_SUBSTITUTION_CONFIDENCE = 0.7


def verify_resolved_via_substitution(
    cache: EvaluationCache,
    library_id: str,
    ill_request_id: str,
    chosen_holding_id: str | None,
    claimed_resolved_via_substitution: bool,
) -> bool:
    """True only when every one of these holds:

    - the caller actually claimed resolved_via_substitution (a claim of
      False can never become True here, regardless of cache contents),
    - a chosen_holding_id was actually supplied (a no-match commit can
      never honestly be "resolved via substitution" -- mirrors
      route_ill_request's own prior chosen_holding_id-is-not-None guard),
    - the ILL Disambiguation Specialist actually ran for this exact
      (library_id, ill_request_id) and wrote a cached result (no cache
      entry means disambiguate_ill_candidates was never called for this
      case -- the exploit this function exists to close),
    - that cached result reached a real convergence (still_ambiguous is
      False) at or above MIN_SUBSTITUTION_CONFIDENCE,
    - and the cached narrowed_candidate_id matches chosen_holding_id --
      the specialist converged on the exact candidate being committed,
      not some other candidate from the same case.
    """
    if not claimed_resolved_via_substitution or chosen_holding_id is None:
        return False
    if cache is None:
        return False
    record = cache.get(library_id, ill_request_id)
    if record is None:
        return False
    if record.get("still_ambiguous", True):
        return False
    if record.get("confidence", 0.0) < MIN_SUBSTITUTION_CONFIDENCE:
        return False
    return record.get("narrowed_candidate_id") == chosen_holding_id
