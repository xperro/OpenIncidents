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
  - the raw LLM token may be stored in the per-user CLI state file during the current planning phase
  - the local CLI state file must live outside the repo and use best-effort restrictive filesystem permissions
  - Secret Manager and Secrets Manager become the preferred hardening path before production use
  - no documentation may silently imply that raw secrets belong in `triage.yaml`
- Mandatory LLM redaction baseline:
  - redact email addresses
  - redact `Authorization`, `Proxy-Authorization`, `Cookie`, and `Set-Cookie` values
  - redact obvious credential-bearing key/value pairs such as `token`, `secret`, `password`, `api_key`, `access_key`, and `secret_key`
  - truncate stack traces and payload excerpts to at most 8000 characters before provider submission

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- GCP infra contract: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md)
- AWS infra contract: [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)
- LLM contract: [../30-integrations/31-llm.md](../30-integrations/31-llm.md)
- CLI local state contract: [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- This document is the canonical home for security and IAM policy.
- GCP and AWS infra documents must link here rather than duplicate policy text.
- LLM submission requires redaction and payload reduction before provider calls.
- Terraform-driven deployment by `triage` does not justify broader standing permissions than the documented resource set requires.
- The documented MVP may persist the raw LLM token only in the per-user CLI state file, never in `triage.yaml` or repo-tracked files.
- Persistent storage of sensitive incident context is not part of the current MVP plan.

## Open questions

- See [OQ-105](../90-open-questions.md#oq-105) for whether the mandatory redaction baseline should expand beyond the documented MVP set.
- See [OQ-107](../90-open-questions.md#oq-107) for the threshold at which cloud secret stores or OS-native secret storage become mandatory.

## Deferred items

- Mandatory Secret Manager or Secrets Manager rollout
- Policy-as-code enforcement
- Audit trails and security review automation
