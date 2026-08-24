import os

import pytest

from stacks.identity.claims import InvalidClaimsError
from stacks.identity.cognito_verifier import CognitoClaimsVerifier


def test_rejects_a_token_with_no_matching_key_id():
    # No live Cognito call needed for this case -- PyJWKClient itself raises
    # before any claim is inspected when the token's kid isn't in the JWKS.
    verifier = CognitoClaimsVerifier(
        user_pool_id="us-west-2_fake00000",
        region="us-west-2",
        app_client_id="fake_client_id",
    )
    with pytest.raises(InvalidClaimsError):
        verifier.verify("not-a-real-jwt")


def test_live_cognito_pool_issues_a_verifiable_token_per_role():
    pool_id = os.environ.get("STACKS_TEST_COGNITO_POOL_ID")
    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    client_id = os.environ.get("STACKS_TEST_COGNITO_APP_CLIENT_ID")
    username = os.environ.get("STACKS_TEST_COGNITO_USERNAME")
    password = os.environ.get("STACKS_TEST_COGNITO_PASSWORD")
    if not all([pool_id, client_id, username, password]):
        pytest.skip("STACKS_TEST_COGNITO_* env vars not set -- run scripts/provision_cognito.py first")

    import boto3
    idp = boto3.client("cognito-idp", region_name=region)
    auth = idp.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    id_token = auth["AuthenticationResult"]["IdToken"]

    verifier = CognitoClaimsVerifier(user_pool_id=pool_id, region=region, app_client_id=client_id)
    claims = verifier.verify(id_token)
    assert claims.role
    assert claims.library_id
