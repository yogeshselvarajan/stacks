output "dynamodb_table_arns" {
  description = "Map of short table name to its ARN, for the IAM module and the repository."
  value       = module.dynamodb.table_arns
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "session_bucket_name" {
  value = module.session_state.bucket_name
}

output "session_bucket_arn" {
  value = module.session_state.bucket_arn
}

output "agent_runtime_execution_role_arn" {
  value = module.iam.agent_runtime_execution_role_arn
}

output "agent_runtime_arn" {
  value = module.agentcore_runtime.agent_runtime_arn
}
