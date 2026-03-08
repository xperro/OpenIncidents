# Summary of `SPECS/chrisloarryn`

## What it is

`SPECS/chrisloarryn/` is the main planning and architecture area for OpenIncidents. It already defines the product shape, the runtime model, the infrastructure targets, the integration contracts, and the unresolved design backlog.

## Core idea

OpenIncidents is documented as a toolkit that turns relevant cloud logs into actionable incidents. The current design centers on:

- a CLI named `triage`
- a Go runtime named `triage-handler`
- optional LLM analysis
- Slack notifications
- optional Jira ticket creation
- support for both GCP and AWS

## Current structure

The directory is intentionally organized by responsibility:

- `00-product-overview.md`: product mission, MVP boundaries, naming, and scope
- `01-system-architecture.md`: end-to-end flow and stable domain contracts
- `10-runtime/`: CLI and handler behavior
- `20-infra/`: GCP and AWS Terraform contracts
- `30-integrations/`: config, LLM, Slack, and Jira contracts
- `40-governance/`: security and IAM baseline
- `90-open-questions.md`: unresolved product and design decisions

## Most important locked decisions

- The repo is still in a documentation-first phase.
- `OpenIncidents` is the project name.
- `triage` is the CLI name.
- `triage-handler` is the runtime name.
- The pipeline reduces events before any LLM step.
- The design stays cloud-agnostic at the product level, while documenting GCP and AWS explicitly.
- Slack, Jira, OpenAI, and Anthropic are the named MVP integrations.

## Runtime and operating model

The documented runtime flow is:

1. ingest a log event
2. normalize it
3. fingerprint and reduce it into an incident
4. evaluate policy
5. optionally call an LLM
6. notify through Slack and optionally Jira

The CLI is expected to initialize projects, generate infrastructure files, optionally run Terraform helpers, and run the handler locally for development.

## Current maturity

This area is conceptually strong and already decomposed into component-level contracts. Its main remaining gaps are not missing structure, but unresolved decisions captured in `90-open-questions.md`.

## Main open decisions still pending

- whether GCP should be the first actual implementation target if scope narrows
- whether GCP should default to Pub/Sub push or a pull-worker model
- whether AWS should default to zip or container packaging
- where dedupe and rate-limit state should live during the MVP
- the exact redaction baseline before sending data to an LLM
- the threshold for creating Jira tickets instead of sending Slack only
- when secret stores become mandatory
- whether `triage` should own `terraform plan/apply` or just generate files
