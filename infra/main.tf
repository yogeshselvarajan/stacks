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
}

module "agentcore_runtime" {
  source              = "./modules/agentcore_runtime"
  environment         = var.environment
  region              = var.region
  execution_role_arn  = module.iam.agent_runtime_execution_role_arn
  artifact_bucket     = var.runtime_artifact_bucket
  artifact_key        = var.runtime_artifact_key
  bedrock_model_id    = var.bedrock_model_id
  agentcore_memory_id = "" # filled in below once Plan 2's memory_id is on hand; see dev.tfvars
  session_bucket_name = module.session_state.bucket_name
  tags                = local.common_tags
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
