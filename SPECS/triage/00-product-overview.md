# OpenIncidents Product Overview
Date: 2026-03-08

## Intent

Define the product framing for OpenIncidents before implementation starts.

## Scope

- In scope for the MVP:
  - turn critical cloud logs into actionable incidents
  - support both GCP and AWS deployment paths as first-class product paths
  - support CLI-driven infrastructure generation, plan, apply, and handler deployment
  - support downloadable handler templates in Go and Python
  - support Python as the official implementation language for the `triage` CLI using only the standard library
  - support Slack and Discord notifications plus Jira ticket creation
  - support optional LLM analysis using OpenAI or Anthropic
  - correlate incidents with context from linked source repositories
  - generate diagnostic output with candidate fixes for operator review
  - support a local development mode for validating the pipeline
- Out of scope for this phase:
  - product code, Terraform modules, template implementation, or automation
  - auto-remediation or corrective actions beyond deployment itself
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
  - CLI-driven cloud deployment remains the main operational path on both GCP and AWS
  - local or development execution remains part of the MVP
- Bootstrap contract:
  - `triage` validates local credentials and required tooling before generation or deployment
  - `triage` generates and applies Terraform as part of the official user journey
  - `triage` downloads handler templates only to an explicit absolute destination path
- Template contract:
  - Go and Python are the two official handler implementation runtimes for the MVP
  - the template target remains `triage-handler` regardless of implementation language
  - `triage-handler` is deployed as a serverless receiver service, not just as an isolated handler function
- CLI implementation contract:
  - the official implementation target for `triage` is Python
  - the CLI uses Python standard-library modules only
  - `argparse` is the baseline for command parsing, help, and subcommand structure
- MVP capability contract:
  - ingest logs from cloud-native sources
  - filter and reduce incidents with error-first policy defaults
  - correlate reduced incidents with linked repository context
  - optionally request structured LLM analysis
  - notify through Slack and Discord and optionally create Jira tickets

## Dependencies

- Entry index: [README.md](README.md)
- Cross-component design: [01-system-architecture.md](01-system-architecture.md)
- Canonical open backlog: [90-open-questions.md](90-open-questions.md)

## Locked decisions

- The repository stays documentation-first until the specs are sufficiently closed.
- OpenIncidents remains cloud-agnostic at the product level while documenting GCP and AWS as equally official deployment targets.
- Slack, Discord, Jira, OpenAI, and Anthropic are the named MVP integrations in the current phase.
- Notification routing is configurable to Slack, Discord, or both, while Jira remains escalation-oriented.
- `triage-handler` is the shared runtime contract name rather than a label for a single language implementation.
- `triage-handler` represents the serverless service that receives pushed log events and processes them.
- `triage` has one official CLI implementation target in Python using only the standard library.
- Go and Python remain the two official handler/runtime implementation paths.
- The product is planned as an open-source toolkit with clear boundaries between stable core contracts and pluggable edges.

## Open questions

- See [OQ-104](90-open-questions.md#oq-104) for the MVP placement of dedupe and rate-limit state.
- See [OQ-106](90-open-questions.md#oq-106) for the final Jira escalation policy relative to Slack and Discord.
- See [OQ-107](90-open-questions.md#oq-107) for the point at which cloud secret stores become mandatory.

## Deferred items

- Additional notifiers beyond Slack, Discord, and Jira
- Additional LLM providers beyond OpenAI and Anthropic
- Auto-remediation workflows
- Persistent storage and long-term incident history
