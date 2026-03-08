# OpenIncidents System Architecture
Date: 2026-03-08

## Intent

Describe the end-to-end system flow and the stable domain contracts that subsystem documents must respect.

## Scope

- In scope:
  - cross-component data flow
  - domain objects shared by runtime, integrations, and infrastructure planning
  - extension boundaries for clouds, notifiers, and LLM providers
- Out of scope:
  - provider-specific resource details
  - exact CLI flag semantics
  - exact IAM policy statements

## Responsibilities

- Define the canonical processing pipeline.
- Own the stable core domain contracts.
- Separate stable internal concepts from pluggable edge integrations.
- Provide the architectural baseline that lower-level documents inherit.

## Contracts

- Canonical flow:
  1. ingest log event
  2. normalize to `NormalizedLogEvent`
  3. fingerprint and reduce into `ReducedIncident`
  4. evaluate `DecisionPolicy`
  5. optionally request LLM analysis and receive `LLMResult`
  6. emit notification payloads for Slack and Jira
- Stable core contracts:
  - `NormalizedLogEvent`: cloud, source, service, env, severity, timestamp, summary, raw excerpt, and source link
  - `ReducedIncident`: fingerprint, aggregation window, count, representative event, reduced context, and truncated stacktrace
  - `DecisionPolicy`: severity threshold, dedupe rules, aggregation window, rate limits, and ticketing thresholds
  - `LLMResult`: strict JSON containing summary, suspected cause, suggested fix, confidence, and ticket-safety signal
- Pluggable edges:
  - sources: GCP, AWS, local
  - notifiers: Slack, Jira, future channels
  - LLM providers: OpenAI, Anthropic, future providers

## Dependencies

- Product baseline: [00-product-overview.md](00-product-overview.md)
- Runtime docs: [10-runtime/10-cli.md](10-runtime/10-cli.md), [10-runtime/11-handler.md](10-runtime/11-handler.md)
- Integration docs: [30-integrations/30-config.md](30-integrations/30-config.md), [30-integrations/31-llm.md](30-integrations/31-llm.md), [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md)
- Infra docs: [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md), [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md)
- Security baseline: [40-governance/40-security-iam.md](40-governance/40-security-iam.md)
- Open backlog: [90-open-questions.md](90-open-questions.md)

## Locked decisions

- The pipeline always reduces raw log data before any optional LLM step.
- The stable core stays vendor-neutral even when edges are provider-specific.
- Local execution is part of the architecture, not a side utility.
- Observability at runtime must preserve request identifiers and incident fingerprints.

## Open questions

- See [OQ-102](90-open-questions.md#oq-102) for the preferred GCP runtime mode.
- See [OQ-103](90-open-questions.md#oq-103) for the default AWS packaging format.
- See [OQ-104](90-open-questions.md#oq-104) for dedupe and rate-limit state storage.
- See [OQ-106](90-open-questions.md#oq-106) for ticket creation thresholds.

## Deferred items

- Additional event sources beyond the initial cloud-native paths
- Persistent incident state or storage-backed dedupe
- Metrics and evaluation pipelines beyond baseline runtime logging
- More plugin surfaces for notifiers and remediation actions
