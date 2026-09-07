# scripts/update_agent_runtime.py
"""Redeploys the real, already-running AgentCore Runtime with the new
deployment package (Task 5's session_manager/PendingApprovals fix).
Uses a direct boto3 control-plane call, not Terraform, since Plan 3's
Terraform tree and state live on branch worktree-stacks-plan3-infrastructure,
not merged to main and not reachable from this plan's own worktree.

Reads the Runtime's existing roleArn and networkConfiguration back via
GetAgentRuntime first, so this call changes only the deployment artifact.

GATED: do not run this until Plan 3's Task 13 (the soak-test
verification) has passed. Run manually, once, from a worktree that has
this plan's Task 5 changes merged or cherry-picked in:

    STACKS_AGENT_RUNTIME_ID=<the real runtime id> \
      STACKS_AWS_REGION=us-west-2 python scripts/update_agent_runtime.py
"""
from __future__ import annotations

import os

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
RUNTIME_ID = os.environ["STACKS_AGENT_RUNTIME_ID"]
ARTIFACT_BUCKET = os.environ.get("STACKS_SESSION_BUCKET", "stacks-session-state-690845170953-us-west-2")
ARTIFACT_KEY = "runtime-artifacts/deployment_package.zip"


def main() -> None:
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    current = client.get_agent_runtime(agentRuntimeId=RUNTIME_ID)

    client.update_agent_runtime(
        agentRuntimeId=RUNTIME_ID,
        roleArn=current["roleArn"],
        networkConfiguration=current["networkConfiguration"],
        agentRuntimeArtifact={
            "codeConfiguration": {
                "entryPoint": ["main.py"],
                "runtime": "PYTHON_3_13",
                "code": {"s3": {"bucket": ARTIFACT_BUCKET, "prefix": ARTIFACT_KEY}},
            }
        },
        environmentVariables=current.get("environmentVariables", {}),
    )
    print(f"Updated agent runtime {RUNTIME_ID} with the new deployment package at s3://{ARTIFACT_BUCKET}/{ARTIFACT_KEY}.")


if __name__ == "__main__":
    main()
