# OpenIncidents Open Questions
Date: 2026-03-08

This file is the canonical backlog for unresolved product and design decisions.

## How to use this file

- Link here whenever a spec needs a decision that is not yet locked.
- Record the current default so implementation does not invent its own fallback later.
- Remove or rewrite an entry only when the corresponding decision is captured in the canonical spec.

## OQ-101

Question: Which cloud should become the first implementation target if the MVP cannot ship both clouds at once?

Current default: keep both GCP and AWS fully documented; if execution scope tightens later, prefer GCP as the first delivered path because the current design is slightly clearer around Pub/Sub and Cloud Run.

Affected docs: [00-product-overview.md](00-product-overview.md), [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md)

## OQ-102

Question: Should the GCP MVP use Pub/Sub push into Cloud Run, or should it favor a pull worker model?

Current default: design for Pub/Sub push into Cloud Run first; keep pull-worker language only as a documented future variant.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md)

## OQ-103

Question: Should the AWS MVP default to a zip package or a container image for `triage-handler`?

Current default: keep both options possible, but favor zip packaging first unless binary size, dependency model, or deployment tooling makes containers clearly simpler.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md)

## OQ-104

Question: Where should dedupe and rate-limit state live during the MVP?

Current default: keep state in memory within a single runtime instance and treat durable shared state as a later concern.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/30-config.md](30-integrations/30-config.md)

## OQ-105

Question: What exact redaction set must always be applied before sending data to an LLM?

Current default: redact emails, obvious tokens, authorization headers, and large stack or payload fragments before provider submission.

Affected docs: [30-integrations/31-llm.md](30-integrations/31-llm.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)

## OQ-106

Question: Under what policy should Jira tickets be created instead of sending Slack only?

Current default: Slack remains the primary notification channel for actionable incidents; Jira creation stays conditional on policy thresholds that still need to be formalized.

Affected docs: [01-system-architecture.md](01-system-architecture.md), [10-runtime/11-handler.md](10-runtime/11-handler.md), [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md)

## OQ-107

Question: At what point should cloud secret stores replace raw environment variables in the MVP path?

Current default: environment variables are acceptable for local development and early documentation, but Secret Manager or Parameter Store should become the expected path before production hardening.

Affected docs: [00-product-overview.md](00-product-overview.md), [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md), [40-governance/40-security-iam.md](40-governance/40-security-iam.md)

## OQ-108

Question: Should the CLI own `terraform plan/apply`, or should it stop at generation and delegate execution to the user?

Current default: keep `infra plan` and `infra apply` in the CLI specification, but treat them as convenience commands rather than as the only valid operating path.

Affected docs: [10-runtime/10-cli.md](10-runtime/10-cli.md), [30-integrations/30-config.md](30-integrations/30-config.md)
