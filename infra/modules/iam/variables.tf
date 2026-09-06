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
