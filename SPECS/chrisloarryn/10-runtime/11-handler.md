# Runtime Specification: `triage-handler`
Date: 2026-03-08

## Intent

Define the Go runtime behavior that receives cloud log events, reduces noise, optionally calls an LLM, and emits actionable notifications.

## Scope

- In scope:
  - ingress from GCP, AWS, and local development sources
  - normalization, fingerprinting, reduction, and decision policy
  - optional LLM invocation and structured result handling
  - emission of Slack and Jira payloads
  - baseline runtime observability
- Out of scope:
  - Terraform resource definitions
  - final Slack and Jira presentation details beyond the payload boundary
  - durable storage or historical analytics

## Responsibilities

- Decode source-specific events into a common internal representation.
- Normalize fields required by the core contracts from [../01-system-architecture.md](../01-system-architecture.md).
- Aggregate repeated events within a bounded window and enforce dedupe behavior.
- Decide whether LLM analysis and notifications should run for a given incident.
- Emit structured payloads for downstream Slack and Jira integrations.
- Include request identifiers and fingerprints in runtime logs.

## Contracts

- Supported ingress paths:
  - GCP Pub/Sub event delivery to the runtime
  - AWS CloudWatch Logs subscription delivery to the runtime
  - local `stdin` or file input for development
- Core runtime defaults:
  - aggregation window: 300 seconds
  - dedupe: one analysis per fingerprint per window
  - stacktrace or payload truncation before notification and LLM submission
- Integration handoff contract:
  - runtime produces incident data with summary, severity, service, env, counts, links, and optional LLM output
  - Slack and Jira formatting rules live in [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Runtime configuration is driven by [../30-integrations/30-config.md](../30-integrations/30-config.md) plus environment variables required by integrations

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
- The runtime stays Go-based in the current design.
- Reduction always happens before optional LLM analysis.
- Runtime logs must include request correlation and incident fingerprint data.

## Open questions

- See [OQ-102](../90-open-questions.md#oq-102) for the preferred GCP event delivery model.
- See [OQ-103](../90-open-questions.md#oq-103) for the default AWS packaging format.
- See [OQ-104](../90-open-questions.md#oq-104) for state placement of dedupe and rate limits.
- See [OQ-106](../90-open-questions.md#oq-106) for Jira ticket creation policy.

## Deferred items

- Durable shared state for dedupe and incident history
- Pull-worker runtime variants beyond the default documented path
- Auto-remediation hooks
- Expanded runtime metrics beyond baseline logging
