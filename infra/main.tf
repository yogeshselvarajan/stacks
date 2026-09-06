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
