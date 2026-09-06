output "bucket_name" {
  value = aws_s3_bucket.session_state.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.session_state.arn
}
