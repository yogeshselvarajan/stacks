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
