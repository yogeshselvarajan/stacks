import os
from unittest.mock import MagicMock

import pytest

from stacks.sequencer.overdue_sequencer import OverdueSequencer


def test_live_session_state_round_trips_through_real_s3():
    bucket = os.environ.get("STACKS_TEST_SESSION_BUCKET")
    region = os.environ.get("STACKS_AWS_REGION", "us-west-2")
    if not bucket:
        pytest.skip("STACKS_TEST_SESSION_BUCKET not set -- point this at a real, disposable S3 bucket to run")

    agent = MagicMock()
    agent.return_value = MagicMock(message="live smoke test tier")

    sequencer = OverdueSequencer(bucket=bucket, region=region, agent_factory=lambda session_id: agent)

    first = sequencer.run_nightly_tier("circ_live_smoke", "lib_demo")
    second = sequencer.run_nightly_tier("circ_live_smoke", "lib_demo")

    assert first["session_id"] == second["session_id"]
    assert second["tier_history_length"] == first["tier_history_length"] + 1
