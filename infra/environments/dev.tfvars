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

# Task 10 (IAM least-privilege hardening): the exact Bedrock model ARN
# build_stacks_agent invokes. Amazon Nova Lite, not Claude Haiku -- the
# deployed model was switched between Task 9 and Task 10 because Claude
# Haiku's Bedrock "model use case details" agreement was NOT_AVAILABLE on
# this account, blocking real invocation; Nova Lite has no such gate and
# is the live, working, deployed model, confirmed via a real smoke test.
bedrock_model_arn = "arn:aws:bedrock:us-west-2:690845170953:inference-profile/us.amazon.nova-lite-v1:0"

# Required in addition to the profile ARN above: Bedrock evaluates IAM
# permissions at both hops for a cross-region inference profile -- the
# profile ARN itself, and whichever regional foundation-model ARN it
# actually dispatches to. Discovered as a real gap post-apply during
# Task 10's smoke-test re-run: a real AccessDeniedException named
# arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0 as
# denied, confirming the profile had routed the call there. All three
# regions this profile can route to (per the routing note above,
# confirmed via `aws bedrock list-inference-profiles`) are listed so the
# next region it happens to route to on a given invocation isn't a
# repeat of this same failure.
bedrock_foundation_model_arns = [
  "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0",
  "arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-lite-v1:0",
  "arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-lite-v1:0",
]

# The real CloudWatch Logs group ARN AgentCore Runtime created for this
# deployment, confirmed via `aws logs describe-log-groups` at Task 10 time.
runtime_log_group_arn_pattern = "arn:aws:logs:us-west-2:690845170953:log-group:/aws/bedrock-agentcore/runtimes/stacks_agent_runtime_dev-NaNK542U2G-DEFAULT:*"
