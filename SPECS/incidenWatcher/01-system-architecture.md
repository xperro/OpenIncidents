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
  1. ingest log event through a cloud adapter or local development source
  2. normalize to `NormalizedLogEvent`
  3. apply error-first filtering, fingerprint, and reduce into `ReducedIncident`
  4. enrich incident context with repository signals from linked repos
  5. evaluate `DecisionPolicy`
  6. optionally request LLM analysis and receive `LLMResult`
  7. emit notification payloads for Slack and Discord and optionally create Jira tickets
- Stable core contracts:
  - `NormalizedLogEvent`: cloud, source, service, env, severity, timestamp, summary, raw excerpt, and source link
  - `ReducedIncident`: fingerprint, aggregation window, count, representative event, reduced context, and truncated stacktrace
  - `RepoContext`: repository id, commit reference, file paths, code excerpts, and confidence score for incident relevance
  - `DecisionPolicy`: severity threshold, dedupe rules, aggregation window, rate limits, routing thresholds, and ticketing thresholds
  - `LLMResult`: strict JSON containing summary, suspected cause, suggested fix, confidence, and escalation-safety signal
- Runtime adapter contract:
  - GCP adapter: Cloud Logging exports to Pub/Sub and reaches `triage-handler` through Pub/Sub push into Cloud Run
  - AWS adapter: CloudWatch Logs reaches `triage-handler` through a log subscription into Lambda
  - local adapter: `stdin` or file replay for development and validation
- Pluggable edges:
  - sources: GCP, AWS, local
  - notifiers: Slack, Discord, Jira, future channels
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
- GCP uses Pub/Sub push into Cloud Run as the canonical delivery model.
- AWS uses CloudWatch Logs subscription into Lambda as the canonical delivery model.
- Observability at runtime must preserve request identifiers and incident fingerprints.

## Open questions

- See [OQ-104](90-open-questions.md#oq-104) for dedupe and rate-limit state storage.
- See [OQ-106](90-open-questions.md#oq-106) for Jira escalation thresholds relative to Slack and Discord.

## Deferred items

- Additional event sources beyond the initial cloud-native paths
- Persistent incident state or storage-backed dedupe
- Metrics and evaluation pipelines beyond baseline runtime logging
- More plugin surfaces for notifiers and remediation actions
