# Infrastructure Specification: AWS Terraform
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the AWS deployment contract for routing CloudWatch Logs into the OpenIncidents runtime.

## Scope

- In scope:
  - CloudWatch Logs subscription wiring
  - Lambda deployment target for `triage-handler`
  - zip packaging as the default deployment artifact
  - Terraform inputs and outputs required by the CLI and runtime
  - default filter guidance for JSON, space-delimited, and text logs
- Out of scope:
  - cross-account subscriptions
  - Kinesis or Firehose delivery
  - duplicated IAM policy detail

## Responsibilities

- Describe the minimum AWS resources required by the MVP path.
- Define the Terraform variables and outputs that other components depend on.
- State the default log filter concepts for CloudWatch Logs subscriptions.
- Define the packaging handoff between `triage` and Terraform.
- Link back to the canonical IAM and security policy instead of re-stating it here.

## Contracts

- MVP resource set:
  - Lambda function for `triage-handler`
  - Lambda execution role
  - CloudWatch Logs subscription filter
  - `aws_lambda_permission` for log delivery
  - zip deployment artifact produced by `triage`
- Default packaging:
  - `zip` is the default package format for both official handler templates
- Default filter concepts:
  - JSON logs derive a field-based OR pattern from the configured `severity_field`
  - space-delimited logs derive a positional pattern from `severity_word_position`
  - text logs default to a broad subscription and runtime-side severity filtering unless `filter_pattern_override` is set
  - exact syntax and examples follow the official [AWS CloudWatch Logs filter pattern syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html)
- CLI workflow contract:
  - `triage` packages the selected handler from an absolute local path into a zip artifact
  - `triage` passes the resolved `lambda_package` into Terraform before `infra apply`
- Core Terraform inputs:
  - `region`
  - `env`
  - `log_group_name`
  - `lambda_name`
  - `lambda_package`
  - `package_format`
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
- `zip` is the default packaging format for the documented AWS MVP path.
- Filter generation may be derived from log shape metadata or replaced with an explicit override.
- AWS filter guidance stays high-level until exact patterns are tested in implementation.
- Secret handling stays at the environment-variable level for the current MVP documentation, with stronger secret-store guidance tracked separately.
- AWS infrastructure detail belongs here, not in runtime or governance documents.

## Open questions

- See [OQ-107](../90-open-questions.md#oq-107) for when Secrets Manager should become mandatory.

## Deferred items

- Cross-account log subscriptions
- Kinesis and Firehose destinations
- Stronger secret-store integration as the default path
