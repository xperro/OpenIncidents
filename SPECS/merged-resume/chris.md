# Summary of `SPECS/incidenWatcher`

## What it is

`SPECS/incidenWatcher/` is the canonical planning and architecture area for OpenIncidents. It defines the product shape, runtime contracts, infrastructure targets, integration contracts, and unresolved design backlog.

## Core idea

OpenIncidents is documented as a toolkit that turns relevant cloud logs into actionable incidents. The current design centers on:

- a CLI named `triage`
- a runtime contract named `triage-handler`
- official support for GCP and AWS
- official handler templates in Go and Python
- repository-context enrichment from linked source repositories
- Slack and Discord notifications
- optional Jira ticket creation
- optional LLM analysis

## Current structure

The directory is intentionally organized by responsibility:

- `00-product-overview.md`: product mission, MVP boundaries, naming, and scope
- `01-system-architecture.md`: end-to-end flow and stable domain contracts
- `10-runtime/`: CLI and handler behavior
- `20-infra/`: GCP and AWS Terraform contracts
- `30-integrations/`: config, LLM, and notification contracts
- `40-governance/`: security and IAM baseline
- `90-open-questions.md`: unresolved product and design decisions

## Most important locked decisions

- The repo is still in a documentation-first phase.
- `OpenIncidents` is the project name.
- `triage` is the CLI name.
- `triage-handler` is the runtime name.
- The pipeline reduces events before any LLM step.
- GCP and AWS are equally official deployment targets in the current documentation.
- `triage` owns template download plus Terraform generation, plan, and apply in the documented user journey.
- Slack, Discord, Jira, OpenAI, and Anthropic are the named MVP integrations.
- Repository enrichment is part of the documented architecture after reduction and before optional LLM analysis.

## Runtime and operating model

The documented runtime flow is:

1. ingest a log event from GCP, AWS, or local replay
2. normalize it
3. fingerprint and reduce it into an incident
4. enrich it with repository context
5. evaluate policy
6. optionally call an LLM
7. notify through Slack and Discord and optionally create Jira tickets

The CLI is expected to initialize projects, download templates, generate infrastructure files, run Terraform helpers, package and deploy handlers, and run the handler locally for development.

## Current maturity

This area is conceptually strong and already decomposed into component-level contracts. Its main remaining gaps are no longer cloud-path selection or packaging defaults; they are the unresolved policy and hardening decisions kept in `90-open-questions.md`.

## Main open decisions still pending

- where dedupe and rate-limit state should live during the MVP
- the exact redaction baseline before sending data to an LLM
- the threshold for creating Jira tickets instead of using Slack and Discord only
- when cloud secret stores become mandatory
