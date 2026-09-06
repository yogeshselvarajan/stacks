variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "agent_runtime_arn" {
  type = string
}

variable "overdue_library_id" {
  type = string
}

variable "overdue_circulation_record_ids" {
  description = "Comma-separated circulation_record_ids the nightly sweep chases. Set by Task 9's seed script output."
  type        = string
}

variable "tags" {
  type = map(string)
}
