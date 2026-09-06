output "dynamodb_table_arns" {
  description = "Map of short table name to its ARN, for the IAM module and the repository."
  value       = module.dynamodb.table_arns
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
