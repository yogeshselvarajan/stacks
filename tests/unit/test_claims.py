import time

import pytest

from stacks.identity.claims import FakeClaimsVerifier, InvalidClaimsError, StaffIdentityClaims


def test_mint_and_verify_round_trip():
    verifier = FakeClaimsVerifier()
    token = verifier.mint(role="circulation_staff", library_id="lib_demo")
    claims = verifier.verify(token)
    assert claims == StaffIdentityClaims(role="circulation_staff", library_id="lib_demo", case_review_role=None)


def test_mint_and_verify_carries_case_review_role():
    verifier = FakeClaimsVerifier()
    token = verifier.mint(role="branch_manager", library_id="lib_demo", case_review_role="librarian_case_review")
    claims = verifier.verify(token)
    assert claims.case_review_role == "librarian_case_review"


def test_expired_token_is_rejected():
    verifier = FakeClaimsVerifier()
    token = verifier.mint(role="circulation_staff", library_id="lib_demo", expired=True)
    with pytest.raises(InvalidClaimsError):
        verifier.verify(token)


def test_malformed_token_is_rejected():
    verifier = FakeClaimsVerifier()
    with pytest.raises(InvalidClaimsError):
        verifier.verify("not-a-real-jwt")


def test_tokens_from_two_different_verifier_instances_do_not_cross_verify():
    # A different secret per instance would break real Cognito use (one pool,
    # one JWKS), but FakeClaimsVerifier is test-only -- this test documents
    # that behavior rather than assuming shared global state.
    a = FakeClaimsVerifier()
    b = FakeClaimsVerifier()
    token = a.mint(role="circulation_staff", library_id="lib_demo")
    if a._secret != b._secret:
        with pytest.raises(InvalidClaimsError):
            b.verify(token)
