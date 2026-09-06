# scripts/seed_overdue_soak_case.py
"""Seeds the one overdue circulation record the real multi-day soak test
tracks. days_overdue only needs to be > 0 for run_overdue_chase to act at
all -- tier advancement is driven entirely by prior_reminder_tier_sent,
not by a specific day-count threshold (confirmed by reading
src/stacks/tools/run_overdue_chase.py directly). Run manually, once:

    STACKS_AWS_REGION=us-west-2 STACKS_ENVIRONMENT=dev python scripts/seed_overdue_soak_case.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.data.models import CirculationRecord

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
LIBRARY_ID = "lib_demo"
CIRCULATION_RECORD_ID = "circ_soak_test_1"


def main() -> None:
    repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    record = CirculationRecord(
        circulation_record_id=CIRCULATION_RECORD_ID, library_id=LIBRARY_ID,
        patron_id="patron_soak_test", item_id="item_soak_test", item_type="book",
        due_date=datetime.now(timezone.utc) - timedelta(days=10),
        prior_reminder_tier_sent=-1,
    )
    repo.save_circulation_record(record)
    print(f"Seeded {CIRCULATION_RECORD_ID} for {LIBRARY_ID}, due_date={record.due_date.isoformat()}.")
    print("Set these in infra/environments/dev.tfvars, then re-run terraform apply:")
    print(f'  overdue_library_id             = "{LIBRARY_ID}"')
    print(f'  overdue_circulation_record_ids = "{CIRCULATION_RECORD_ID}"')


if __name__ == "__main__":
    main()
