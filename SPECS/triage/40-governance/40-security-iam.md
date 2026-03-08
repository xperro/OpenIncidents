# Governance Specification: Security and IAM
Date: 2026-03-08

## Intent

Define the canonical security posture and IAM baseline for OpenIncidents across runtime, integrations, and cloud infrastructure.

## Scope

- In scope:
  - least-privilege principles
  - cloud IAM boundaries for GCP and AWS
  - secret-handling expectations
  - LLM data-safety expectations
- Out of scope:
  - provider-specific secret manager implementation detail
  - full policy-as-code artifacts
  - compliance programs or audit workflows

## Responsibilities

- Own the cross-cutting rules that infra and runtime documents must reference.
- Define the minimum expected permissions for cloud components.
- Define the baseline secret-handling posture for the MVP.
- Define what must not be sent to an LLM by default.

## Contracts

- Security principles:
  - least privilege
  - no silent expansion of permissions
  - no secrets or obvious PII sent to LLM providers by default
- GCP IAM baseline:
  - the logging sink writer identity must receive Pub/Sub publish permission
  - the Pub/Sub push identity must receive permission to invoke the Cloud Run service
  - the Cloud Run service account should keep only runtime-required permissions
  - the local operator identity used by `triage` should have only the permissions needed to run Terraform and publish the documented handler artifact
- AWS IAM baseline:
  - CloudWatch Logs requires invoke permission on the Lambda target
  - the Lambda execution role starts with basic runtime logging only plus outbound permissions required by enabled integrations
  - the local operator identity used by `triage` should have only the permissions needed to run Terraform and update the documented Lambda package
- Secret-handling baseline:
  - environment variables are acceptable for the documented MVP path
  - local `.env` is acceptable for development only and must stay out of version control
  - Secret Manager and Secrets Manager become the preferred hardening path before production use
  - no documentation may silently imply that raw secrets belong in `triage.yaml`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- GCP infra contract: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md)
- AWS infra contract: [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)
- LLM contract: [../30-integrations/31-llm.md](../30-integrations/31-llm.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- This document is the canonical home for security and IAM policy.
- GCP and AWS infra documents must link here rather than duplicate policy text.
- LLM submission requires redaction and payload reduction before provider calls.
- Terraform-driven deployment by `triage` does not justify broader standing permissions than the documented resource set requires.
- Persistent storage of sensitive incident context is not part of the current MVP plan.

## Open questions

- See [OQ-105](../90-open-questions.md#oq-105) for the exact mandatory redaction baseline.
- See [OQ-107](../90-open-questions.md#oq-107) for the threshold at which cloud secret stores become mandatory.

## Deferred items

- Mandatory Secret Manager or Secrets Manager rollout
- Policy-as-code enforcement
- Audit trails and security review automation
