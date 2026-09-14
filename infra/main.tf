provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  common_tags = merge(var.tags, { Environment = var.environment })
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  environment = var.environment
  tags        = local.common_tags
}

module "session_state" {
  source      = "./modules/session_state"
  account_id  = data.aws_caller_identity.current.account_id
  region      = var.region
  environment = var.environment
  tags        = local.common_tags
}

module "iam" {
  source                        = "./modules/iam"
  environment                   = var.environment
  tags                          = local.common_tags
  dynamodb_table_arns           = values(module.dynamodb.table_arns)
  session_bucket_arn            = module.session_state.bucket_arn
  agentcore_memory_arn          = var.agentcore_memory_arn
  bedrock_model_arn             = var.bedrock_model_arn
  bedrock_foundation_model_arns = var.bedrock_foundation_model_arns
  runtime_log_group_arn_pattern = var.runtime_log_group_arn_pattern
  agent_runtime_arn             = module.agentcore_runtime.agent_runtime_arn
  # Real Bedrock Guardrail ARN, constructed the same way AWS itself
  # names the resource -- empty until bedrock_guardrail_id is set, which
  # falls back to the iam module's own wildcard default (see that
  # module's variables.tf for why).
  bedrock_guardrail_arn = var.bedrock_guardrail_id != "" ? "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:guardrail/${var.bedrock_guardrail_id}" : ""
}

module "agentcore_runtime" {
  source              = "./modules/agentcore_runtime"
  environment         = var.environment
  region              = var.region
  execution_role_arn  = module.iam.agent_runtime_execution_role_arn
  artifact_bucket     = var.runtime_artifact_bucket
  artifact_key        = var.runtime_artifact_key
  bedrock_model_id          = var.bedrock_model_id
  agentcore_memory_id       = var.agentcore_memory_id_short
  bedrock_guardrail_id      = var.bedrock_guardrail_id
  bedrock_guardrail_version = var.bedrock_guardrail_version
  session_bucket_name       = module.session_state.bucket_name
  tags                      = local.common_tags
}

module "eventbridge_sequencer" {
  source                         = "./modules/eventbridge_sequencer"
  environment                    = var.environment
  region                         = var.region
  agent_runtime_arn              = module.agentcore_runtime.agent_runtime_arn
  overdue_library_id             = var.overdue_library_id
  overdue_circulation_record_ids = var.overdue_circulation_record_ids
  tags                           = local.common_tags
}

resource "aws_budgets_budget" "stacks_informational" {
  name         = "stacks-informational-${var.environment}"
  budget_type  = "COST"
  limit_amount = "15"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "ABSOLUTE_VALUE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}

resource "aws_budgets_budget" "stacks_hard_stop" {
  name         = "stacks-hard-stop-${var.environment}"
  budget_type  = "COST"
  limit_amount = "35"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "ABSOLUTE_VALUE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
