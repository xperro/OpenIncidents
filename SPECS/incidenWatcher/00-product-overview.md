# OpenIncidents Product Overview
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the product framing for OpenIncidents before implementation starts.

## Scope

- In scope for the MVP:
  - turn critical cloud logs into actionable incidents
  - support both GCP and AWS deployment paths
  - support Slack or Discord notifications
  - support optional LLM analysis using OpenAI or Anthropic
  - correlate incidents with context from linked source repositories
  - generate diagnostic output with candidate fixes for operator review
  - support a local development mode for validating the pipeline
- Out of scope for this phase:
  - product code, Terraform modules, generators, or runtime implementation
  - auto-remediation or deploy actions
  - full raw log streaming into an LLM
  - vendor lock-in in the core domain model

## Responsibilities

- Define the product mission and MVP boundaries.
- Own the naming contract for project, CLI, and runtime.
- Describe who the documentation serves and how it should be read.
- Lock the repository-level planning baseline before component-specific detail.

## Contracts

- Naming contract:
  - project name: `OpenIncidents`
  - CLI name: `triage`
  - runtime name: `triage-handler`
- Delivery modes:
  - CLI-driven cloud deployment remains the main operational path
  - local or development execution remains part of the MVP
- MVP capability contract:
  - ingest logs from cloud-native sources
  - filter and reduce incidents with error-first policy defaults
  - correlate reduced incidents with linked repository context
  - optionally request structured LLM analysis
  - notify through Slack or Discord

## Dependencies

- Entry index: [README.md](README.md)
- Cross-component design: [01-system-architecture.md](01-system-architecture.md)
- Canonical open backlog: [90-open-questions.md](90-open-questions.md)

## Locked decisions

- The repository stays documentation-first until the specs are sufficiently closed.
- OpenIncidents remains cloud-agnostic at the product level while documenting GCP and AWS equally.
- GCP is the first implementation target; AWS remains available in the configuration and documentation model.
- Slack, Discord, OpenAI, and Anthropic are the named MVP integrations in the current phase.
- Notification routing is configurable to Slack, Discord, or both.
- Python is the target implementation language for the first runtime delivery.
- The product is planned as an open-source toolkit with clear boundaries between stable core contracts and pluggable edges.

## Open questions

- See [OQ-107](90-open-questions.md#oq-107) for the point at which cloud secret stores become mandatory.
- See [OQ-111](90-open-questions.md#oq-111) for Jira reintroduction policy after the Slack/Discord MVP baseline.

## Deferred items

- Additional notifiers beyond Slack and Discord
- Jira reintegration as a post-MVP notifier/escalation target
- Additional LLM providers beyond OpenAI and Anthropic
- Auto-remediation workflows
- Persistent storage and long-term incident history
