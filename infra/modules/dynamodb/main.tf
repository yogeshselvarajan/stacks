resource "aws_dynamodb_table" "bookings" {
  name         = "Stacks-Bookings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "booking_id"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "booking_id"
    type = "S"
  }
  attribute {
    name = "room_key"
    type = "S"
  }
  attribute {
    name = "start"
    type = "S"
  }

  global_secondary_index {
    name            = "room_time_index"
    hash_key        = "room_key"
    range_key       = "start"
    projection_type = "ALL"
  }

  tags = merge(var.tags, { Name = "Stacks-Bookings-${var.environment}" })
}

resource "aws_dynamodb_table" "ill_requests" {
  name         = "Stacks-ILLRequests-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "ill_request_id"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "ill_request_id"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-ILLRequests-${var.environment}" })
}

resource "aws_dynamodb_table" "items" {
  name         = "Stacks-Items-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "title"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "title"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-Items-${var.environment}" })
}

resource "aws_dynamodb_table" "loans" {
  name         = "Stacks-Loans-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "circulation_record_id"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "circulation_record_id"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-Loans-${var.environment}" })
}

resource "aws_dynamodb_table" "policy_rules" {
  name         = "Stacks-PolicyRules-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "policy_name"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "policy_name"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-PolicyRules-${var.environment}" })
}

resource "aws_dynamodb_table" "audit_log" {
  name         = "Stacks-AuditLog-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "sequence"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "sequence"
    type = "N"
  }

  tags = merge(var.tags, { Name = "Stacks-AuditLog-${var.environment}" })
}

resource "aws_dynamodb_table" "spaces" {
  name         = "Stacks-Spaces-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "space_id"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "space_id"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-Spaces-${var.environment}" })
}

resource "aws_dynamodb_table" "patrons" {
  name         = "Stacks-Patrons-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "library_id"
  range_key    = "patron_id"

  attribute {
    name = "library_id"
    type = "S"
  }
  attribute {
    name = "patron_id"
    type = "S"
  }

  tags = merge(var.tags, { Name = "Stacks-Patrons-${var.environment}" })
}
