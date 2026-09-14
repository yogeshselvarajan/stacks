# src/stacks/guardrails/bedrock_guardrail.py
"""Real Bedrock Guardrails check, replacing notify_parties.py's Plan 1
hardcoded-denylist stand-in. Uses the standalone ApplyGuardrail API (not
model-inference-time application) so the call site notify_parties.py
already has (unconditional, before every send) does not change -- only
what backs the check does. See scripts/provision_bedrock_guardrail.py
for how the real guardrail resource this calls is created.
"""
from __future__ import annotations

import boto3


class BedrockGuardrailClient:
    """Checks arbitrary text against a real, provisioned Bedrock
    Guardrail via ApplyGuardrail. `source="OUTPUT"` since this always
    checks agent-composed content before it is sent, never raw user
    input.
    """

    def __init__(self, guardrail_id: str, guardrail_version: str, region: str) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._guardrail_id = guardrail_id
        self._guardrail_version = guardrail_version

    def check(self, text: str) -> list[str]:
        response = self._client.apply_guardrail(
            guardrailIdentifier=self._guardrail_id,
            guardrailVersion=self._guardrail_version,
            source="OUTPUT",
            content=[{"text": {"text": text}}],
        )
        if response.get("action") != "GUARDRAIL_INTERVENED":
            return []

        findings: list[str] = []
        for assessment in response.get("assessments", []):
            word_policy = assessment.get("wordPolicy") or {}
            for word in word_policy.get("customWords", []):
                findings.append(f"blocked_word: {word.get('match')}")

            sensitive_info = assessment.get("sensitiveInformationPolicy") or {}
            for entity in sensitive_info.get("piiEntities", []):
                findings.append(f"blocked_pii: {entity.get('type')}")

            for regex_match in sensitive_info.get("regexes", []):
                findings.append(f"blocked_pii_regex: {regex_match.get('name')}")

        return findings or ["blocked_by_bedrock_guardrail"]
