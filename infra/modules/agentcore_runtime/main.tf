resource "aws_bedrockagentcore_agent_runtime" "stacks" {
  agent_runtime_name = "stacks_agent_runtime_${var.environment}"
  description        = "Stacks library-operations agent. Good Neighbor Agents hackathon entry."
  role_arn           = var.execution_role_arn

  agent_runtime_artifact {
    code_configuration {
      entry_point = ["main.py"]
      runtime     = "PYTHON_3_13"

      code {
        s3 {
          bucket = var.artifact_bucket
          prefix = var.artifact_key
        }
      }
    }
  }

  environment_variables = {
    STACKS_AWS_REGION          = var.region
    STACKS_ENVIRONMENT         = var.environment
    STACKS_BEDROCK_MODEL_ID    = var.bedrock_model_id
    STACKS_AGENTCORE_MEMORY_ID = var.agentcore_memory_id
    STACKS_SESSION_BUCKET      = var.session_bucket_name
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  tags = merge(var.tags, { Name = "stacks-agent-runtime-${var.environment}" })
}
