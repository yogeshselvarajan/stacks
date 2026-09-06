"""Populates the real DynamoDB tables with the same demo dataset
stacks.data.fixtures.seed_demo_library defines, so the three canonical
demo scenarios work identically against the real backend. Run manually,
any number of times (idempotent -- every write is a put_item on a fixed
key):

    python scripts/seed_dynamodb.py

Never imported by test code.
"""
from __future__ import annotations

import os

from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.data.fixtures import seed_demo_library

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")


def main() -> None:
    repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    seed_demo_library(repo, library_id="lib_demo")
    print(f"Seeded lib_demo into the real DynamoDB tables (environment={ENVIRONMENT}, region={REGION}).")


if __name__ == "__main__":
    main()
