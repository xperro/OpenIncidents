# Infrastructure Specification: AWS Terraform
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the AWS deployment contract for routing CloudWatch Logs into the OpenIncidents runtime.

## Scope

- In scope:
  - CloudWatch Logs subscription wiring
  - Lambda deployment target for `triage-handler`
  - Terraform inputs and outputs required by the CLI and runtime
  - default filter guidance for JSON and text logs
- Out of scope:
  - cross-account subscriptions
  - Kinesis or Firehose delivery
  - duplicated IAM policy detail

## Responsibilities

- Describe the minimum AWS resources required by the MVP path.
- Define the Terraform variables and outputs that other components depend on.
- State the default log filter concepts for CloudWatch Logs subscriptions.
- Link back to the canonical IAM and security policy instead of re-stating it here.

## Contracts

- MVP resource set:
  - Lambda function for `triage-handler`
  - Lambda execution role
  - CloudWatch Logs subscription filter
  - `aws_lambda_permission` for log delivery
- Default filter concepts:
  - JSON logs may use field-based severity patterns
  - text logs may use string-based severity patterns
  - exact filter syntax must be documented and validated once implementation begins
- Core Terraform inputs:
  - `region`
  - `env`
  - `log_group_name`
  - `lambda_name`
  - `lambda_package`
  - `filter_name`
  - `filter_pattern`
- Core Terraform outputs:
  - `lambda_arn`
  - `subscription_filter_name`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Security and IAM: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- The AWS path is documented as CloudWatch Logs subscription to Lambda.
- AWS remains configurable in the MVP contract, but delivery sequencing prioritizes GCP first.
- AWS filter guidance stays high-level until exact patterns are tested.
- Secret handling stays at the environment-variable level for the current MVP documentation, with stronger secret-store guidance tracked separately.
- AWS infrastructure detail belongs here, not in runtime or governance documents.

## Open questions

- See [OQ-103](../90-open-questions.md#oq-103) for the default Lambda packaging format.
- See [OQ-107](../90-open-questions.md#oq-107) for when Parameter Store or Secrets Manager should become mandatory.

## Deferred items

- Cross-account log subscriptions
- Kinesis and Firehose destinations
- Stronger secret-store integration as the default path
