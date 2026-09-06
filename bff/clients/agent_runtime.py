# bff/clients/agent_runtime.py
"""AgentRuntimeClient -- the BFF's abstraction over invoking the deployed
AgentCore Runtime. FakeAgentRuntimeClient lets Task 17 build and test the
entire write/resume endpoint correctly before Task 18's real Runtime
redeploy exists. BedrockAgentCoreRuntimeClient's own call shape is
confirmed against the real, installed boto3 service model and matches
Plan 3's own scripts/smoke_test_runtime.py exactly (agentRuntimeArn and
payload required; runtimeSessionId/contentType/accept all real,
settable fields).
"""
from __future__ import annotations

import json
from typing import Any, Protocol


class AgentRuntimeClient(Protocol):
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class FakeAgentRuntimeClient:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        # Default canned response represents a genuinely resolved resume
        # (stop_reason != "interrupt", tool_outcome == "committed") --
        # matching main.py's real _run_chat response shape (Task 17 fix
        # round, I1) so tests that don't care about the outcome check
        # keep passing; tests that do pass their own response override.
        self._response = response or {"status": "ok", "stop_reason": "end_turn", "tool_outcome": "committed"}

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return self._response


class BedrockAgentCoreRuntimeClient:
    """Not exercised end to end until Task 19 -- constructing this object
    makes no network call itself (boto3 clients are lazy)."""

    def __init__(self, region: str, agent_runtime_arn: str, boto_session=None) -> None:
        import boto3

        session = boto_session or boto3.Session(region_name=region)
        self._client = session.client("bedrock-agentcore", region_name=region)
        self._agent_runtime_arn = agent_runtime_arn

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.invoke_agent_runtime(
            agentRuntimeArn=self._agent_runtime_arn,
            runtimeSessionId=payload["session_id"],
            contentType="application/json",
            accept="application/json",
            payload=json.dumps(payload).encode("utf-8"),
        )
        body = response["response"].read()
        return json.loads(body.decode("utf-8"))
