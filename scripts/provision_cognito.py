"""One-time setup: creates the Stacks Cognito user pool, four groups, and
one test user per group, per docs/architecture/agent_architecture.md
section 4.5's table. Run manually:

    python scripts/provision_cognito.py

Never imported by test code -- provisioning is a deliberate, reviewed,
human-triggered action (Global Constraints).
"""
from __future__ import annotations

import os
import secrets

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
POOL_NAME = "stacks-staff-pool"

GROUPS = [
    {"GroupName": "circulation_staff"},
    {"GroupName": "room_booking_staff"},
    {"GroupName": "ill_coordinator"},
    {"GroupName": "branch_manager"},
]

TEST_USERS = [
    {"username": "test-circulation-staff", "group": "circulation_staff", "library_id": "lib_demo", "case_review_role": None},
    {"username": "test-room-booking-staff", "group": "room_booking_staff", "library_id": "lib_demo", "case_review_role": None},
    {"username": "test-ill-coordinator", "group": "ill_coordinator", "library_id": "lib_demo", "case_review_role": None},
    {"username": "test-branch-manager", "group": "branch_manager", "library_id": "lib_demo", "case_review_role": "librarian_case_review"},
]


def main() -> None:
    idp = boto3.client("cognito-idp", region_name=REGION)

    pool = idp.create_user_pool(
        PoolName=POOL_NAME,
        Schema=[
            {"Name": "library_id", "AttributeDataType": "String", "Mutable": True},
            {"Name": "case_review_role", "AttributeDataType": "String", "Mutable": True},
        ],
        AutoVerifiedAttributes=[],
    )
    pool_id = pool["UserPool"]["Id"]
    print(f"Created user pool: {pool_id}")

    client = idp.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="stacks-test-client",
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        GenerateSecret=False,
    )
    client_id = client["UserPoolClient"]["ClientId"]
    print(f"Created app client: {client_id}")

    for group in GROUPS:
        idp.create_group(UserPoolId=pool_id, **group)
        print(f"Created group: {group['GroupName']}")

    for user in TEST_USERS:
        password = secrets.token_urlsafe(16) + "1!Aa"
        attrs = [{"Name": "custom:library_id", "Value": user["library_id"]}]
        if user["case_review_role"]:
            attrs.append({"Name": "custom:case_review_role", "Value": user["case_review_role"]})
        idp.admin_create_user(
            UserPoolId=pool_id, Username=user["username"],
            UserAttributes=attrs, MessageAction="SUPPRESS", TemporaryPassword=password,
        )
        idp.admin_set_user_password(UserPoolId=pool_id, Username=user["username"], Password=password, Permanent=True)
        idp.admin_add_user_to_group(UserPoolId=pool_id, Username=user["username"], GroupName=user["group"])
        print(f"Created test user {user['username']} in group {user['group']}, password: {password}")

    print()
    print("Set these before running the live tests:")
    print(f"  STACKS_TEST_COGNITO_POOL_ID={pool_id}")
    print(f"  STACKS_TEST_COGNITO_APP_CLIENT_ID={client_id}")
    print("  STACKS_TEST_COGNITO_USERNAME=test-branch-manager")
    print("  STACKS_TEST_COGNITO_PASSWORD=<the password printed above for that user>")


if __name__ == "__main__":
    main()
