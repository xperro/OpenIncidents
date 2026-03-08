# OpenIncidents System Architecture
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

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
  3. apply error-first filtering and fingerprint into `ReducedIncident`
  4. enrich incident context with repository signals from linked repos
  5. evaluate `DecisionPolicy`
  6. optionally request LLM analysis and receive `LLMResult`
  7. emit notification payloads for Slack or Discord
- Stable core contracts:
  - `NormalizedLogEvent`: cloud, source, service, env, severity, timestamp, summary, raw excerpt, and source link
  - `ReducedIncident`: fingerprint, aggregation window, count, representative event, reduced context, and truncated stacktrace
  - `RepoContext`: repository id, commit reference, file paths, code excerpts, and confidence score for incident relevance
  - `DecisionPolicy`: severity threshold, dedupe rules, aggregation window, rate limits, and notification routing thresholds
  - `LLMResult`: strict JSON containing summary, suspected cause, suggested fix, confidence, and escalation-safety signal
- Pluggable edges:
  - sources: GCP, AWS, local
  - notifiers: Slack, Discord, future channels
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
- Repository enrichment happens after reduction so LLM input stays bounded and relevant.
- The stable core stays vendor-neutral even when edges are provider-specific.
- Local execution is part of the architecture, not a side utility.
- Repository enrichment uses Git repository sources declared in config with credential indirection through environment variables.
- Observability at runtime must preserve request identifiers and incident fingerprints.

## Open questions

- See [OQ-102](90-open-questions.md#oq-102) for the preferred GCP runtime mode.
- See [OQ-103](90-open-questions.md#oq-103) for the default AWS packaging format.
- See [OQ-104](90-open-questions.md#oq-104) for dedupe and rate-limit state storage.
- See [OQ-106](90-open-questions.md#oq-106) for channel routing granularity (global vs service-level).

## Deferred items

- Additional event sources beyond the initial cloud-native paths
- Persistent incident state or storage-backed dedupe
- Metrics and evaluation pipelines beyond baseline runtime logging
- More plugin surfaces for notifiers and remediation actions
