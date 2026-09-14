variable "environment" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "dynamodb_table_arns" {
  description = "The 8 table ARNs from the dynamodb module's output map."
  type        = list(string)
}

variable "session_bucket_arn" {
  type = string
}

variable "agentcore_memory_arn" {
  description = "The Plan 2-provisioned AgentCore Memory resource's ARN. Empty string if not yet known (falls back to a wildcard, tightened once set)."
  type        = string
  default     = ""
}

variable "bedrock_guardrail_arn" {
  description = "The real, provisioned Bedrock Guardrail's ARN (scripts/provision_bedrock_guardrail.py). Empty string if not yet known (falls back to a wildcard, tightened once set) -- mirrors agentcore_memory_arn's own pattern above. Found live, 2026-09-14: the runtime's own STACKS_BEDROCK_GUARDRAIL_ID/VERSION env vars were already set and notify_parties was already calling the real ApplyGuardrail API, but this role had never been granted bedrock:ApplyGuardrail at all -- every real notify_parties call failed with a live AccessDeniedException, even though local tests (which default to the denylist stand-in, never a real AWS call) never exercised this path."
  type        = string
  default     = ""
}

variable "bedrock_model_arn" {
  description = "The exact Bedrock model/inference-profile ARN build_stacks_agent invokes, confirmed working by Task 7's smoke test."
  type        = string
}

variable "bedrock_foundation_model_arns" {
  description = "The underlying regional foundation-model ARNs the bedrock_model_arn cross-region inference profile may route to. Required in addition to the profile ARN itself -- Bedrock checks IAM permissions at both hops. Discovered as a real gap during Task 10's post-hardening smoke-test re-run (AccessDeniedException naming the exact missing us-east-1 foundation-model ARN)."
  type        = list(string)
  default     = []
}

variable "runtime_log_group_arn_pattern" {
  description = "The CloudWatch Logs group ARN pattern AgentCore Runtime actually created for this deployment, confirmed by inspecting the real log group name after Task 7's first invocation."
  type        = string
}

variable "agent_runtime_arn" {
  type = string
}
