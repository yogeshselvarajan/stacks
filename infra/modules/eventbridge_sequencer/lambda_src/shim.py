# infra/modules/eventbridge_sequencer/lambda_src/shim.py
"""EventBridge nightly-schedule shim Lambda. Its only job: call the
deployed AgentCore Runtime's invoke_agent_runtime API once, in
overdue_sequencer_nightly_sweep mode, for a small, fixed, configured list
of circulation_record_ids.

Deliberately not a dynamic DynamoDB scan for every open overdue case --
building that scan is a named, honest scope decision this plan defers
(see Task 9's own note), so the real soak test can start as early as
possible.
"""
from __future__ import annotations

import json
import os
import uuid

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["STACKS_AGENT_RUNTIME_ARN"]
LIBRARY_ID = os.environ["STACKS_OVERDUE_LIBRARY_ID"]
CIRCULATION_RECORD_IDS = os.environ["STACKS_OVERDUE_CIRCULATION_RECORD_IDS"].split(",")

_client = boto3.client("bedrock-agentcore", region_name=REGION)


def handler(event, context):
    session_id = "overdue-sweep-" + uuid.uuid4().hex + "-" + uuid.uuid4().hex
    payload = {
        "mode": "overdue_sequencer_nightly_sweep",
        "library_id": LIBRARY_ID,
        "circulation_record_ids": CIRCULATION_RECORD_IDS,
        "session_id": session_id,
    }
    response = _client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode("utf-8"),
    )
    body = response["response"].read().decode("utf-8")
    print(f"overdue sweep result: {body}")
    return {"statusCode": 200, "body": body}
