# scripts/provision_pending_approvals_table.py
"""One-time setup: creates the real Stacks-PendingApprovals-<env> DynamoDB
table. NOT Terraform-managed like Plan 3's 8 tables -- Plan 3's infra/
Terraform tree lives on branch worktree-stacks-plan3-infrastructure, not
yet merged to main, and this plan's own worktree branches from main, so
that tree is not reachable here. This follows the exact precedent Plan 2
already set for the same situation (scripts/provision_cognito.py,
scripts/provision_agentcore_memory.py): a standalone boto3 script for a
real AWS resource needed before its owning Terraform tree can reach it.
A later merge of Plan 3's branch can fold this table into
infra/modules/dynamodb/ as a 9th table, as a pure refactor that does not
touch the already-created resource.

Idempotent: checks for existence before creating, safe to run more than
once. Run manually:

    STACKS_AWS_REGION=us-west-2 STACKS_ENVIRONMENT=dev python scripts/provision_pending_approvals_table.py

Never imported by test code.
"""
from __future__ import annotations

import os

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
TABLE_NAME = f"Stacks-PendingApprovals-{ENVIRONMENT}"


def main() -> None:
    client = boto3.client("dynamodb", region_name=REGION)
    existing = client.list_tables().get("TableNames", [])
    if TABLE_NAME in existing:
        print(f"{TABLE_NAME} already exists in {REGION}, nothing to do.")
        return

    client.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "library_id", "AttributeType": "S"},
            {"AttributeName": "case_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "library_id", "KeyType": "HASH"},
            {"AttributeName": "case_id", "KeyType": "RANGE"},
        ],
        Tags=[{"Key": "Project", "Value": "stacks"}, {"Key": "Environment", "Value": ENVIRONMENT}],
    )
    client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
    print(f"Created {TABLE_NAME} in {REGION}.")


if __name__ == "__main__":
    main()
