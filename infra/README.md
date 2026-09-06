# Stacks infrastructure

Terraform-managed AWS infrastructure for Stacks (Good Neighbor Agents
hackathon entry). See `docs/superpowers/plans/2026-09-06-stacks-plan3-infrastructure.md`
for the full build history and rationale.

## Prerequisites

- Terraform >= 1.5, AWS credentials configured (account 690845170953).
- `hashicorp/aws` provider >= 6.63, < 7.0 and `hashicorp/archive` >= 2.4, < 3.0 (pulled automatically by `terraform init`).
- `infra/environments/dev.tfvars` must set every variable that has no
  default in `infra/variables.tf`. As of Task 11, that is:
  - `bedrock_model_id` -- the Bedrock model ID or inference profile ID the
    deployed agent invokes. Currently `us.amazon.nova-lite-v1:0` (see
    "Why Amazon Nova Lite, not Claude Haiku" below).
  - `bedrock_model_arn` -- the same model's inference-profile ARN.
  - `bedrock_foundation_model_arns` -- has a default of `[]`, but in
    practice must be set to the list of regional foundation-model ARNs a
    cross-region inference profile can dispatch to (IAM checks
    permissions at both the profile ARN and whichever regional model ARN
    Bedrock actually routes the call to). Currently the three regions
    `us.amazon.nova-lite-v1:0` can route to: `us-east-1`, `us-west-2`,
    `us-east-2`.
  - `runtime_artifact_bucket` / `runtime_artifact_key` -- the S3 bucket
    and key holding the AgentCore Runtime deployment package.
  - `runtime_log_group_arn_pattern` -- the real CloudWatch Logs group ARN
    AgentCore Runtime creates for this deployment, needed to scope the
    execution role's logging permissions instead of leaving them
    wildcarded.
  - `budget_alert_email` -- the email address AWS Budgets notifies at the
    $15 informational and $35 hard-stop thresholds.
  - `overdue_library_id` / `overdue_circulation_record_ids` have defaults
    (`lib_demo` / `circ_soak_test_1`), already pointed at the real
    soak-test case seeded in Task 9; only override them for a different
    demo case.
  - `agentcore_memory_arn` defaults to an empty string and is left unset
    intentionally (see "Known gap" below) until Plan 2's
    `scripts/provision_agentcore_memory.py` is actually run in this
    account.

## Apply

```bash
cd infra
terraform init
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

## Outputs this project's scripts and environment variables need

| Terraform output | Feeds into |
|---|---|
| `dynamodb_table_arns` | `infra/modules/iam`'s DynamoDB policy scoping |
| `session_bucket_name` | `STACKS_SESSION_BUCKET` env var (main.py, OverdueSequencer, scripts/upload_deployment_package.py) |
| `agent_runtime_arn` | `STACKS_AGENT_RUNTIME_ARN` env var (scripts/smoke_test_runtime.py, the shim Lambda) |
| `agent_runtime_execution_role_arn` | `infra/modules/agentcore_runtime`'s `execution_role_arn` input |
| `bff_execution_role_arn` | Plan 4's BFF, not yet built |
| `overdue_shim_lambda_name` | manual `aws lambda invoke` calls during the soak test |

## Why Amazon Nova Lite, not Claude Haiku

The agent was originally built and smoke-tested against Claude Haiku 4.5.
Task 7's deployment discovered that this AWS account's Bedrock "model use
case details" agreement for Anthropic models was not available
(`agreementAvailability: NOT_AVAILABLE`), which blocked the first real
model invocation. Amazon Nova Lite (`us.amazon.nova-lite-v1:0`) has
`agreementAvailability: AVAILABLE` on this account with no extra
agreement step, and it supports tool use via the Converse API, which
Strands' `BedrockModel` relies on for this agent's tool-calling. Nova
Lite is this model family's cheap/fast dev-iteration tier, the same role
Haiku played in `docs/architecture/cost_estimate.md`'s model strategy, so
the switch changes which model is deployed, not the cost or architecture
plan. Both `bedrock_model_id` and `bedrock_model_arn` in
`environments/dev.tfvars` reflect this real, deployed model, confirmed
working by a real smoke test (`scripts/smoke_test_runtime.py`), not by
assumption.

## Known gap: `AgentCoreMemory` IAM statement is wildcard-scoped

`infra/modules/iam/main.tf`'s `AgentCoreMemory` statement
(`bedrock-agentcore:GetMemory`, `CreateEvent`, `RetrieveMemoryRecords`,
`GetMemoryRecord`) is scoped to `resources = ["*"]` rather than a real
ARN. This is because no real AgentCore Memory resource has been
provisioned in this account yet -- Plan 2's
`scripts/provision_agentcore_memory.py` has not been run here. This is a
known, already-documented, accepted gap (see the inline HCL comment in
that file), not an oversight and not something this task fixes. Once
`provision_agentcore_memory.py` is run and produces a real memory ARN,
set `agentcore_memory_arn` in `environments/dev.tfvars` to that ARN and
re-apply; the ternary in `main.tf` narrows the statement automatically.
Do not assume every IAM statement in this project is already
least-privilege scoped without checking this one first.

## Destroy

**Do not run this while the Overdue Escalation Sequencer's multi-day soak
test (started in Task 9 of the plan above, at 2026-09-06T09:47:09Z UTC)
is still being observed, and not before Task 13's verification is
recorded.** Once the soak test and judging period are both done:

```bash
cd infra
terraform plan -destroy -var-file=environments/dev.tfvars   # review first
terraform destroy -var-file=environments/dev.tfvars
```

This tears down all 24 resources this project's Terraform state tracks:
8 DynamoDB tables, the session-state S3 bucket and its 2 sub-resources
(lifecycle configuration, public-access block), 2 IAM roles and their 2
inline policies, the AgentCore Runtime, the EventBridge rule/target/
permission and shim Lambda and its own IAM role/policy (6 resources), and
both AWS Budgets.

A `terraform plan -destroy -var-file=environments/dev.tfvars` dry run was
verified on 2026-09-06 (no real destroy was run) and reported **24 to
destroy**, not the 26 originally estimated when this plan's tasks were
written. Reconciled: the earlier estimate double-counted the `iam`
module's resources. Task 5 actually added 2 resources
(`aws_iam_role.agent_runtime_execution`,
`aws_iam_role_policy.agent_runtime_baseline`, confirmed by that task's own
`Apply complete! Resources: 2 added` output), not 4 as the original
arithmetic assumed; Task 10 then added the other 2
(`aws_iam_role.bff_execution`, `aws_iam_role_policy.bff_policy`), for 4
real `iam`-module resources total, not 6. Every other task's contribution
(Task 1: 8, Task 4: 3, Task 7: 1, Task 8: 6, Task 11: 2) matched exactly.
The dry-run's 24 resource addresses were individually checked against
`terraform state list` (32 entries, of which 8 are data sources that
`destroy` never acts on: `data.aws_caller_identity`, one `archive_file`,
and 6 `aws_iam_policy_document` data sources) -- every resource this
project created is present in the destroy plan; nothing is missing.
