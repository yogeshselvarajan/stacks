"""Manual smoke test for the deployed AgentCore Runtime. Run after
terraform apply:

    STACKS_AGENT_RUNTIME_ARN=<Task 7's agent_runtime_arn output> \
      STACKS_AWS_REGION=us-west-2 python scripts/smoke_test_runtime.py
"""
from __future__ import annotations

import json
import os
import uuid

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["STACKS_AGENT_RUNTIME_ARN"]


def main() -> None:
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    # Padded well past any minimum length AgentCore Runtime may enforce on
    # runtimeSessionId -- a defensive precaution, not a value confirmed
    # against AWS docs this session.
    session_id = "smoke-test-" + uuid.uuid4().hex + "-" + uuid.uuid4().hex
    payload = {
        "prompt": "Call get_library_data for query_type room_calendar, library_id lib_demo, room_id room_a, "
                  "start 2026-09-01T00:00:00+00:00, end 2026-09-02T00:00:00+00:00, and summarize what you find.",
        "role": "branch_manager",
        "library_id": "lib_demo",
        "case_review_role": "librarian_case_review",
        "session_id": session_id,
    }
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode("utf-8"),
    )
    body = response["response"].read()
    print(body.decode("utf-8"))


if __name__ == "__main__":
    main()
