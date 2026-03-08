# OpenIncidents Product Overview
Date: 2026-03-08

## Intent

Define the product framing for OpenIncidents before implementation starts.

## Scope

- In scope for the MVP:
  - turn critical cloud logs into actionable incidents
  - support both GCP and AWS deployment paths
  - support Slack notifications and Jira ticket creation
  - support optional LLM analysis using OpenAI or Anthropic
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
  - reduce and classify incidents
  - optionally request structured LLM analysis
  - notify through Slack and optionally Jira

## Dependencies

- Entry index: [README.md](README.md)
- Cross-component design: [01-system-architecture.md](01-system-architecture.md)
- Canonical open backlog: [90-open-questions.md](90-open-questions.md)

## Locked decisions

- The repository stays documentation-first until the specs are sufficiently closed.
- OpenIncidents remains cloud-agnostic at the product level while documenting GCP and AWS equally.
- Slack, Jira, OpenAI, and Anthropic are the only named MVP integrations in the current phase.
- The product is planned as an open-source toolkit with clear boundaries between stable core contracts and pluggable edges.

## Open questions

- See [OQ-101](90-open-questions.md#oq-101) for first implementation target priority if scope forces a single cloud first.
- See [OQ-107](90-open-questions.md#oq-107) for the point at which cloud secret stores become mandatory.

## Deferred items

- Additional notifiers beyond Slack and Jira
- Additional LLM providers beyond OpenAI and Anthropic
- Auto-remediation workflows
- Persistent storage and long-term incident history
