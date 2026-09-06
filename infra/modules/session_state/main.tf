resource "aws_s3_bucket" "session_state" {
  bucket = "stacks-session-state-${var.account_id}-${var.region}"
  tags   = merge(var.tags, { Name = "stacks-session-state-${var.environment}" })
}

resource "aws_s3_bucket_public_access_block" "session_state" {
  bucket                  = aws_s3_bucket.session_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "session_state" {
  bucket = aws_s3_bucket.session_state.id

  rule {
    id     = "expire-sessions"
    status = "Enabled"

    filter {
      prefix = "sessions/"
    }

    expiration {
      days = 7
    }
  }
}
