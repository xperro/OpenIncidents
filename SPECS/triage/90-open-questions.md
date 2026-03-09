# OpenIncidents Open Questions
Date: 2026-03-08

This file is the canonical backlog for unresolved product and design decisions.

## How to use this file

- Link here whenever a spec needs a decision that is not yet locked.
- Record the current default so implementation does not invent its own fallback later.
- Remove or rewrite an entry only when the corresponding decision is captured in the canonical spec.

## OQ-104

Question: When should the MVP move from per-instance in-memory dedupe and rate-limit state to durable shared state?

Current default: keep state in memory within a single warm runtime instance and accept that Cloud Run and Lambda may emit duplicate notifications across parallel instances during the MVP.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/30-config.md](30-integrations/30-config.md)

## OQ-105

Question: What additional redaction rules should be added beyond the mandatory MVP baseline before broader rollout?

Current default: redact email addresses, `Authorization` and `Proxy-Authorization` headers, `Cookie` and `Set-Cookie` values, obvious credential-bearing key/value pairs such as `token`, `secret`, `password`, `api_key`, `access_key`, and `secret_key`, and truncate stack or payload excerpts to 8000 characters before provider submission.

Affected docs: [30-integrations/31-llm.md](30-integrations/31-llm.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)

## OQ-106

Question: When should Jira escalation expand beyond the baseline severity-only policy?

Current default: Slack and Discord remain the primary outbound notification channels for actionable incidents, and Jira tickets are created only when Jira is enabled and the reduced incident severity is greater than or equal to `CRITICAL`.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/30-config.md](30-integrations/30-config.md), [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md)

## OQ-107

Question: At what point should cloud secret stores replace raw environment variables in the MVP path?

Current default: environment variables are acceptable for local development, and the per-user CLI local state file is acceptable for bootstrap-time LLM token persistence during the current documentation phase, but GCP Secret Manager, AWS Secrets Manager, or stronger local secret storage should become the expected path before production hardening.

Affected docs: [00-product-overview.md](00-product-overview.md), [10-runtime/12-cli-state.md](10-runtime/12-cli-state.md), [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md), [30-integrations/30-config.md](30-integrations/30-config.md), [30-integrations/31-llm.md](30-integrations/31-llm.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)

## OQ-108

Question: When repository snippets are added to `repo_context`, should LLM execution stay one-call-per-incident or switch to batched calls with strict shared token budgets?

Current default: keep one call per incident with aggressive local filtering and bounded context; revisit batching only after repository-context precision and token profiles are measured in real workloads.

Affected docs: [10-runtime/10-cli.md](10-runtime/10-cli.md), [30-integrations/31-llm.md](30-integrations/31-llm.md)
