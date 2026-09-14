# scripts/provision_bedrock_guardrail.py
"""Creates the real Bedrock Guardrail notify_parties.py checks every
outgoing notification against, replacing the Plan 1 hardcoded-denylist
stand-in with an actual AWS-managed policy. Run manually, once per
environment:

    STACKS_AWS_REGION=us-west-2 python scripts/provision_bedrock_guardrail.py

Idempotent: if a guardrail named "stacks-notify-parties-guardrail-<env>"
already exists, prints its id/version instead of creating a duplicate.
Prints the STACKS_BEDROCK_GUARDRAIL_ID / STACKS_BEDROCK_GUARDRAIL_VERSION
env vars to set for main.py and the BFF.
"""
from __future__ import annotations

import os

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
GUARDRAIL_NAME = f"stacks-notify-parties-guardrail-{ENVIRONMENT}"

# Mirrors notify_parties.py's own pre-existing _GUARDRAIL_DENYLIST exactly,
# so the real Guardrail is a strict upgrade (same coverage, backed by a
# real AWS-managed policy) rather than a behavior change.
DENYLIST_WORDS = ("social security number", "ssn:", "credit card")


def main() -> None:
    client = boto3.client("bedrock", region_name=REGION)

    existing = _find_existing_guardrail(client)
    if existing is not None:
        print(f"Guardrail already exists: id={existing['id']} version={existing['version']}")
        _print_env_vars(existing["id"], existing["version"])
        return

    response = client.create_guardrail(
        name=GUARDRAIL_NAME,
        description="Blocks patron-identifying financial/SSN content and known-sensitive phrases in every Stacks notification before it is sent.",
        wordPolicyConfig={
            "wordsConfig": [
                {"text": word, "inputAction": "BLOCK", "outputAction": "BLOCK"}
                for word in DENYLIST_WORDS
            ],
        },
        sensitiveInformationPolicyConfig={
            "piiEntitiesConfig": [
                {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK", "inputAction": "BLOCK", "outputAction": "BLOCK"},
                {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK", "inputAction": "BLOCK", "outputAction": "BLOCK"},
            ],
        },
        blockedInputMessaging="This request was blocked by a content safety policy.",
        blockedOutputsMessaging="This content was blocked by a content safety policy.",
    )
    guardrail_id = response["guardrailId"]

    version_response = client.create_guardrail_version(
        guardrailIdentifier=guardrail_id,
        description="Initial version: SSN/credit-card word and PII policies.",
    )
    guardrail_version = version_response["version"]

    print(f"Created guardrail: id={guardrail_id} version={guardrail_version}")
    _print_env_vars(guardrail_id, guardrail_version)


def _find_existing_guardrail(client) -> dict | None:
    paginator = client.get_paginator("list_guardrails")
    for page in paginator.paginate():
        for summary in page["guardrails"]:
            if summary["name"] == GUARDRAIL_NAME:
                return {"id": summary["id"], "version": summary["version"]}
    return None


def _print_env_vars(guardrail_id: str, guardrail_version: str) -> None:
    print("Set these for main.py and the BFF:")
    print(f"  STACKS_BEDROCK_GUARDRAIL_ID={guardrail_id}")
    print(f"  STACKS_BEDROCK_GUARDRAIL_VERSION={guardrail_version}")


if __name__ == "__main__":
    main()
