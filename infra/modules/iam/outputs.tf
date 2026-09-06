output "agent_runtime_execution_role_arn" {
  value = aws_iam_role.agent_runtime_execution.arn
}

output "bff_execution_role_arn" {
  value = aws_iam_role.bff_execution.arn
}
