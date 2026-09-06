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
    sid       = "BedrockInvokeScoped"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    # Real, IAM-required grant for a cross-region Bedrock inference
    # profile: Bedrock evaluates permissions at both hops -- the
    # inference-profile ARN itself, AND whichever regional foundation-model
    # ARN the profile dispatches to under the hood. Granting the profile
    # ARN alone is not sufficient. Discovered by re-running Task 7's smoke
    # test after this task's first apply: a real AccessDeniedException
    # named the exact missing permission (ConverseStream denied on
    # arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0),
    # confirming the profile had routed the call to us-east-1. The
    # bedrock_foundation_model_arns list below covers all three regions
    # this profile can route to (us-east-1, us-west-2, us-east-2, per
    # infra/environments/dev.tfvars' own routing note).
    resources = concat([var.bedrock_model_arn], var.bedrock_foundation_model_arns)
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
    sid       = "CloudWatchLogsScoped"
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [var.runtime_log_group_arn_pattern]
  }

  statement {
    sid       = "AgentCoreMemory"
    effect    = "Allow"
    actions   = ["bedrock-agentcore:GetMemory", "bedrock-agentcore:CreateEvent", "bedrock-agentcore:RetrieveMemoryRecords", "bedrock-agentcore:GetMemoryRecord"]
    resources = var.agentcore_memory_arn != "" ? [var.agentcore_memory_arn] : ["*"]
    # KNOWN, ACCEPTED GAP (Task 10, IAM least-privilege hardening pass):
    # this statement remains wildcard-scoped ("*") because no real
    # AgentCore Memory resource exists in this AWS account yet. Verified
    # at Task 10 time via `aws bedrock-agentcore-control list-memories
    # --region us-west-2`, which returned zero memories -- Plan 2's
    # scripts/provision_agentcore_memory.py has not been run in this
    # account. There is genuinely no real ARN to narrow this to right
    # now, so it is not narrowed with an invented placeholder. This is a
    # named, accepted exception to this task's own least-privilege goal,
    # not an oversight: once provision_agentcore_memory.py is run and
    # produces a real memory ARN, set agentcore_memory_arn (in
    # infra/environments/dev.tfvars) to that ARN and re-apply, which
    # narrows this statement automatically via the ternary above.
  }
}

resource "aws_iam_role_policy" "agent_runtime_baseline" {
  name   = "stacks-agent-runtime-baseline-${var.environment}"
  role   = aws_iam_role.agent_runtime_execution.id
  policy = data.aws_iam_policy_document.agent_runtime_baseline.json
}

# The BFF execution role, unused until Plan 4's frontend/BFF exists, per
# final_architecture.md section 10.6's already-decided role table
# ("cheap to provision now").
data "aws_iam_policy_document" "bff_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "bff_execution" {
  name               = "stacks-bff-execution-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.bff_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "bff_policy" {
  statement {
    sid       = "InvokeRuntime"
    effect    = "Allow"
    actions   = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = [var.agent_runtime_arn]
  }

  statement {
    sid       = "DynamoDBReadOnly"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = concat(var.dynamodb_table_arns, [for arn in var.dynamodb_table_arns : "${arn}/index/*"])
    # No write actions -- the BFF never writes to DynamoDB directly, only
    # via the agent's own tools, per final_architecture.md section 10.6.
  }
}

resource "aws_iam_role_policy" "bff_policy" {
  name   = "stacks-bff-policy-${var.environment}"
  role   = aws_iam_role.bff_execution.id
  policy = data.aws_iam_policy_document.bff_policy.json
}
