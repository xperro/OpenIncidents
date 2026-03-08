# Runtime Specification: `triage-handler`
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the Python runtime behavior that receives cloud log events, reduces noise, enriches with linked repository context, optionally calls an LLM, and emits actionable notifications.

## Scope

- In scope:
  - ingress from GCP, AWS, and local development sources
  - normalization, error filtering, fingerprinting, reduction, and decision policy
  - repository context lookup from linked Git repositories (with optional local cache path)
  - optional LLM invocation and structured result handling
  - emission of Slack and Discord payloads
  - baseline runtime observability
- Out of scope:
  - Terraform resource definitions
  - final Slack and Discord presentation details beyond the payload boundary
  - durable storage or historical analytics

## Responsibilities

- Decode source-specific events into a common internal representation.
- Normalize fields required by the core contracts from [../01-system-architecture.md](../01-system-architecture.md).
- Aggregate repeated events within a bounded window and enforce dedupe behavior.
- Retrieve relevant code context from linked repositories using incident-derived search keys.
- Decide whether LLM analysis and notifications should run for a given incident.
- Emit structured payloads for downstream Slack and Discord integrations.
- Include request identifiers and fingerprints in runtime logs.

## Contracts

- Supported ingress paths:
  - GCP Pub/Sub event delivery to the runtime
  - AWS CloudWatch Logs subscription delivery to the runtime
  - local `stdin` or file input for development
- Core runtime defaults:
  - severity filter: `ERROR` and `CRITICAL` by default
  - aggregation window: 300 seconds
  - dedupe: one analysis per fingerprint per window
  - stacktrace or payload truncation before notification and LLM submission
- Integration handoff contract:
  - runtime produces incident data with summary, severity, service, env, counts, links, and optional LLM output
  - Slack and Discord formatting rules live in [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Runtime configuration is driven by [../30-integrations/30-config.md](../30-integrations/30-config.md), local `.env` for development, plus environment variables required by integrations

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- LLM contract: [../30-integrations/31-llm.md](../30-integrations/31-llm.md)
- Notification contract: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Infra context: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md), [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage-handler` remains the runtime name.
- The runtime implementation target is Python in the current design.
- Reduction always happens before optional LLM analysis.
- Linked repository access uses config-declared Git URLs with credential references from environment variables.
- Runtime logs must include request correlation and incident fingerprint data.

## Open questions

- See [OQ-102](../90-open-questions.md#oq-102) for the preferred GCP event delivery model.
- See [OQ-103](../90-open-questions.md#oq-103) for the default AWS packaging format.
- See [OQ-104](../90-open-questions.md#oq-104) for state placement of dedupe and rate limits.
- See [OQ-106](../90-open-questions.md#oq-106) for channel routing granularity (global vs service-level).

## Deferred items

- Durable shared state for dedupe and incident history
- Pull-worker runtime variants beyond the default documented path
- Auto-remediation hooks
- Expanded runtime metrics beyond baseline logging
