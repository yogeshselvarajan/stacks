output "lambda_function_name" {
  value = aws_lambda_function.shim.function_name
}

output "rule_arn" {
  value = aws_cloudwatch_event_rule.nightly.arn
}
