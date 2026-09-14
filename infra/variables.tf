variable "region" {
  description = "AWS region every resource in this project is deployed to."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Single-environment name used as a suffix on every resource this project creates."
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Common tags applied to every resource this project creates."
  type        = map(string)
  default = {
    Project = "stacks"
  }
}

variable "agentcore_memory_arn" {
  description = "Plan 2's provisioned AgentCore Memory resource ARN (from scripts/provision_agentcore_memory.py's own output). Leave empty until known."
  type        = string
  default     = ""
}

variable "agentcore_memory_id_short" {
  description = "The same resource as agentcore_memory_arn, but the bare id (STACKS_AGENTCORE_MEMORY_ID) main.py's AgentCoreMemoryStore actually expects."
  type        = string
  default     = ""
}

variable "bedrock_guardrail_id" {
  description = "Real Bedrock Guardrail id (scripts/provision_bedrock_guardrail.py's own output). Empty string if not yet provisioned."
  type        = string
  default     = ""
}

variable "bedrock_guardrail_version" {
  type    = string
  default = ""
}

variable "bedrock_model_id" {
  description = "The Bedrock model ID or inference profile ID the deployed agent invokes. No guessed default -- must be set explicitly in dev.tfvars."
  type        = string
}

variable "runtime_artifact_bucket" {
  description = "S3 bucket holding the AgentCore Runtime deployment package (Task 6's upload target)."
  type        = string
}

variable "runtime_artifact_key" {
  description = "S3 key (prefix) of the uploaded deployment package zip (Task 6's upload target)."
  type        = string
}

variable "overdue_library_id" {
  type    = string
  default = "lib_demo"
}

variable "overdue_circulation_record_ids" {
  description = "Placeholder until Task 9 seeds a real overdue case and supplies its circulation_record_id."
  type        = string
  default     = "circ_soak_test_1"
}

variable "bedrock_model_arn" {
  type = string
}

variable "bedrock_foundation_model_arns" {
  description = "The underlying regional foundation-model ARNs the bedrock_model_arn cross-region inference profile may route to (required in addition to the profile ARN; see infra/modules/iam/variables.tf)."
  type        = list(string)
  default     = []
}

variable "runtime_log_group_arn_pattern" {
  type = string
}

variable "budget_alert_email" {
  description = "Email address AWS Budgets notifies at each threshold. Set this yourself -- not defaulted here."
  type        = string
}
