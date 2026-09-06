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
