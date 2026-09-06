data "aws_iam_policy_document" "agent_runtime_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agent_runtime_execution" {
  name               = "stacks-agent-runtime-execution-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.agent_runtime_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "agent_runtime_baseline" {
  statement {
    sid       = "BedrockInvokeUnscoped"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = ["*"]
    # Intentionally unscoped for now. Task 10 narrows this to the exact
    # model/inference-profile ARN once the bedrock_model_id used in Task
    # 7's deployment is confirmed working end to end.
  }

  statement {
    sid       = "DynamoDBAccess"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = concat(var.dynamodb_table_arns, [for arn in var.dynamodb_table_arns : "${arn}/index/*"])
  }

  statement {
    sid       = "S3SessionState"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = [var.session_bucket_arn, "${var.session_bucket_arn}/*"]
  }

  statement {
    sid       = "CloudWatchLogsUnscoped"
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
    # Intentionally unscoped for now. Task 10 narrows this to the specific
    # log group AgentCore Runtime actually creates, confirmed by
    # inspecting the real log group name after Task 7's first invocation.
  }

  statement {
    sid       = "AgentCoreMemory"
    effect    = "Allow"
    actions   = ["bedrock-agentcore:GetMemory", "bedrock-agentcore:CreateEvent", "bedrock-agentcore:RetrieveMemoryRecords", "bedrock-agentcore:GetMemoryRecord"]
    resources = var.agentcore_memory_arn != "" ? [var.agentcore_memory_arn] : ["*"]
  }
}

resource "aws_iam_role_policy" "agent_runtime_baseline" {
  name   = "stacks-agent-runtime-baseline-${var.environment}"
  role   = aws_iam_role.agent_runtime_execution.id
  policy = data.aws_iam_policy_document.agent_runtime_baseline.json
}
