variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "execution_role_arn" {
  type = string
}

variable "artifact_bucket" {
  type = string
}

variable "artifact_key" {
  type = string
}

variable "bedrock_model_id" {
  description = "The Bedrock model ID or inference profile ID build_stacks_agent invokes. No guessed default -- must be set explicitly, matching agent.py's own STACKS_BEDROCK_MODEL_ID convention."
  type        = string
}

variable "agentcore_memory_id" {
  type    = string
  default = ""
}

variable "bedrock_guardrail_id" {
  description = "Real Bedrock Guardrail id (scripts/provision_bedrock_guardrail.py). Empty string if not yet provisioned."
  type        = string
  default     = ""
}

variable "bedrock_guardrail_version" {
  type    = string
  default = ""
}

variable "session_bucket_name" {
  type = string
}

variable "tags" {
  type = map(string)
}
