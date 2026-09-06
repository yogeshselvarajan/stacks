data "archive_file" "shim" {
  type        = "zip"
  source_file = "${path.module}/lambda_src/shim.py"
  output_path = "${path.module}/build/shim.zip"
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "shim_lambda" {
  name               = "stacks-overdue-shim-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "shim_lambda_policy" {
  statement {
    sid       = "InvokeRuntime"
    effect    = "Allow"
    actions   = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = [var.agent_runtime_arn]
  }

  statement {
    sid       = "Logs"
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "shim_lambda" {
  name   = "stacks-overdue-shim-policy-${var.environment}"
  role   = aws_iam_role.shim_lambda.id
  policy = data.aws_iam_policy_document.shim_lambda_policy.json
}

resource "aws_lambda_function" "shim" {
  function_name    = "stacks-overdue-shim-${var.environment}"
  role             = aws_iam_role.shim_lambda.arn
  handler          = "shim.handler"
  runtime          = "python3.13"
  filename         = data.archive_file.shim.output_path
  source_code_hash = data.archive_file.shim.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      STACKS_AWS_REGION                     = var.region
      STACKS_AGENT_RUNTIME_ARN              = var.agent_runtime_arn
      STACKS_OVERDUE_LIBRARY_ID             = var.overdue_library_id
      STACKS_OVERDUE_CIRCULATION_RECORD_IDS = var.overdue_circulation_record_ids
    }
  }

  tags = merge(var.tags, { Name = "stacks-overdue-shim-${var.environment}" })
}

resource "aws_cloudwatch_event_rule" "nightly" {
  name                = "stacks-overdue-nightly-${var.environment}"
  description         = "Nightly trigger for the Overdue Escalation Sequencer."
  schedule_expression = "cron(0 8 * * ? *)"
  tags                = merge(var.tags, { Name = "stacks-overdue-nightly-${var.environment}" })
}

resource "aws_cloudwatch_event_target" "nightly_shim" {
  rule = aws_cloudwatch_event_rule.nightly.name
  arn  = aws_lambda_function.shim.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.shim.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nightly.arn
}
