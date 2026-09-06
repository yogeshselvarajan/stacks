region      = "us-west-2"
environment = "dev"

# agentcore_memory_arn = "arn:aws:bedrock-agentcore:us-west-2:690845170953:memory/REPLACE_ME"

# Switched from Claude Haiku 4.5 to Amazon Nova Lite. Claude Haiku's
# agreementAvailability was NOT_AVAILABLE on this account (Bedrock's
# Anthropic "model use case details" agreement had not been submitted),
# blocking the real soak test's first invocation. Nova Lite's
# agreementAvailability is AVAILABLE with no extra agreement step (confirmed
# via `aws bedrock get-foundation-model-availability --model-id
# amazon.nova-lite-v1:0 --region us-west-2`), and it supports tool use via
# the Converse API, which Strands' BedrockModel relies on for this agent's
# tool-calling. Real cross-region inference profile ID confirmed via
# `aws bedrock list-inference-profiles --region us-west-2` (routes through
# us-east-1, us-west-2, us-east-2). Nova Lite is this family's
# cheap/fast dev-iteration tier, the same role Haiku played in
# cost_estimate.md's model strategy.
bedrock_model_id        = "us.amazon.nova-lite-v1:0"
runtime_artifact_bucket = "stacks-session-state-690845170953-us-west-2"
runtime_artifact_key    = "runtime-artifacts/deployment_package.zip"

# overdue_library_id / overdue_circulation_record_ids: Task 9 seeded the
# real soak-test overdue record (scripts/seed_overdue_soak_case.py) and
# sets the real values here explicitly.
overdue_library_id             = "lib_demo"
overdue_circulation_record_ids = "circ_soak_test_1"
