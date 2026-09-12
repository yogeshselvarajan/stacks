# scripts/verify_soak_session.py
"""Reads the soak-test case's real S3-backed session state and prints its
tier_history, for a human to review after several real nights have
passed since Task 9's kickoff. Run manually:

    STACKS_SESSION_BUCKET=<Task 4's bucket_name output> \
      STACKS_AWS_REGION=us-west-2 python scripts/verify_soak_session.py
"""
from __future__ import annotations

import os

from strands.session.s3_session_manager import S3SessionManager

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
BUCKET = os.environ["STACKS_SESSION_BUCKET"]
SESSION_ID = "overdue:lib_demo:circ_soak_test_1"
AGENT_ID = "overdue_sequencer"


def main() -> None:
    session_manager = S3SessionManager(session_id=SESSION_ID, bucket=BUCKET, region_name=REGION)
    session_agent = session_manager.read_agent(SESSION_ID, AGENT_ID)
    if session_agent is None:
        print("No session state found yet -- has the nightly schedule fired at least once (Task 9)?")
        return

    tier_history = session_agent.state.get("tier_history", [])
    print(f"tier_history has {len(tier_history)} entries:")
    for i, entry in enumerate(tier_history):
        print(f"  [{i}] run_at={entry['run_at']} stop_reason={entry['stop_reason']} interrupt_ids={entry['interrupt_ids']}")

    from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository

    repo = DynamoDBLibraryDataRepository(region=REGION, environment=os.environ.get("STACKS_ENVIRONMENT", "dev"))
    record = repo.get_circulation_record("lib_demo", "circ_soak_test_1")
    print(f"prior_reminder_tier_sent (real DynamoDB record) = {record.prior_reminder_tier_sent}")


if __name__ == "__main__":
    main()
