region      = "us-west-2"
environment = "dev"

# agentcore_memory_arn = "arn:aws:bedrock-agentcore:us-west-2:690845170953:memory/REPLACE_ME"

# Real Claude Haiku 4.5 cross-region inference profile ID, confirmed via
# `aws bedrock list-inference-profiles --region us-west-2` against this
# account. Haiku, not Sonnet, per cost_estimate.md's guidance to run the
# cheaper model for development/iteration workloads (which is exactly what
# this deployment's multi-day soak test is) and reserve Sonnet for the final
# demo recording and judging-period spot checks.
bedrock_model_id        = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
runtime_artifact_bucket = "stacks-session-state-690845170953-us-west-2"
runtime_artifact_key    = "runtime-artifacts/deployment_package.zip"
