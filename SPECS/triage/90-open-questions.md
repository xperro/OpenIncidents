# OpenIncidents Open Questions
Date: 2026-03-08

This file is the canonical backlog for unresolved product and design decisions.

## How to use this file

- Link here whenever a spec needs a decision that is not yet locked.
- Record the current default so implementation does not invent its own fallback later.
- Remove or rewrite an entry only when the corresponding decision is captured in the canonical spec.

## OQ-104

Question: Where should dedupe and rate-limit state live during the MVP?

Current default: keep state in memory within a single runtime instance and treat durable shared state as a later concern.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/30-config.md](30-integrations/30-config.md)

## OQ-105

Question: What exact redaction set must always be applied before sending data to an LLM?

Current default: redact emails, obvious tokens, authorization headers, and large stack or payload fragments before provider submission.

Affected docs: [30-integrations/31-llm.md](30-integrations/31-llm.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)

## OQ-106

Question: Under what policy should Jira tickets be created instead of sending Slack or Discord notifications only?

Current default: Slack and Discord remain the primary outbound notification channels for actionable incidents; Jira creation stays conditional on policy thresholds that still need to be formalized.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/30-config.md](30-integrations/30-config.md), [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md)

## OQ-107

Question: At what point should cloud secret stores replace raw environment variables in the MVP path?

Current default: environment variables are acceptable for local development and early documentation, but GCP Secret Manager and AWS Secrets Manager should become the expected path before production hardening.

Affected docs: [00-product-overview.md](00-product-overview.md), [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)
