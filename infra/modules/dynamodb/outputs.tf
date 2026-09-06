output "table_arns" {
  value = {
    bookings     = aws_dynamodb_table.bookings.arn
    ill_requests = aws_dynamodb_table.ill_requests.arn
    items        = aws_dynamodb_table.items.arn
    loans        = aws_dynamodb_table.loans.arn
    policy_rules = aws_dynamodb_table.policy_rules.arn
    audit_log    = aws_dynamodb_table.audit_log.arn
    spaces       = aws_dynamodb_table.spaces.arn
    patrons      = aws_dynamodb_table.patrons.arn
  }
}

output "table_names" {
  value = {
    bookings     = aws_dynamodb_table.bookings.name
    ill_requests = aws_dynamodb_table.ill_requests.name
    items        = aws_dynamodb_table.items.name
    loans        = aws_dynamodb_table.loans.name
    policy_rules = aws_dynamodb_table.policy_rules.name
    audit_log    = aws_dynamodb_table.audit_log.name
    spaces       = aws_dynamodb_table.spaces.name
    patrons      = aws_dynamodb_table.patrons.name
  }
}
