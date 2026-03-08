# Runtime Specification: `triage-handler`
Date: 2026-03-08

## Intent

Define the shared runtime behavior of `triage-handler` across the official Go and Python templates, including repository enrichment and multichannel notification handoff.

## Scope

- In scope:
  - ingress from GCP, AWS, and local development sources
  - normalization, error filtering, fingerprinting, reduction, and decision policy
  - repository context lookup from linked Git repositories (with optional local cache path)
  - optional LLM invocation and structured result handling
  - emission of Slack, Discord, and Jira payloads
  - baseline runtime observability
- Out of scope:
  - Terraform resource definitions
  - final Slack, Discord, and Jira presentation details beyond the payload boundary
  - durable storage or historical analytics

## Responsibilities

- Decode source-specific events into a common internal representation.
- Normalize fields required by the core contracts from [../01-system-architecture.md](../01-system-architecture.md).
- Aggregate repeated events within a bounded window and enforce dedupe behavior.
- Retrieve relevant code context from linked repositories using incident-derived search keys.
- Decide whether LLM analysis and notifications should run for a given incident.
- Emit structured payloads for downstream Slack, Discord, and Jira integrations.
- Include request identifiers and fingerprints in runtime logs.

## Contracts

- Official template runtimes:
  - Go
  - Python
- Language-specific implementation detail:
  - Go-specific handler design lives in [../triage-handler-go/README.md](../triage-handler-go/README.md)
  - Python-specific handler design lives in [../triage-handler-python/README.md](../triage-handler-python/README.md)
- CLI language independence:
  - the language chosen for `triage` does not constrain the handler implementation language
  - Go and Python remain valid handler implementations regardless of the CLI implementation being Python
- Supported ingress paths:
  - GCP Pub/Sub push delivery to an HTTP endpoint on Cloud Run
  - AWS CloudWatch Logs subscription delivery to a Lambda handler
  - local `stdin` or file input for development
- Core runtime defaults:
  - severity filter: `ERROR` and `CRITICAL` by default
  - aggregation window: 300 seconds
  - dedupe: one analysis per fingerprint per window
  - stacktrace or payload truncation before notification and LLM submission
- Integration handoff contract:
  - runtime produces incident data with summary, severity, service, env, counts, links, and optional LLM output
  - Slack, Discord, and Jira formatting rules live in [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Template minimum contract:
  - load config from `triage.yaml` plus referenced environment variables
  - normalize source payloads to the same internal representation across Go and Python
  - apply severity thresholds before notification and ticket creation
  - ship notifier clients for Slack, Discord, and Jira
  - expose a basic local development mode for replaying payloads
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
- The runtime contract is language-agnostic even though official templates are provided in Go and Python.
- Shared runtime behavior stays in this document; language-specific implementation detail belongs in `triage-handler-go/` and `triage-handler-python/`.
- GCP traffic reaches the runtime through Pub/Sub push on Cloud Run.
- AWS traffic reaches the runtime through CloudWatch Logs subscription delivery on Lambda.
- Reduction always happens before optional LLM analysis.
- Linked repository access uses config-declared Git URLs with credential references from environment variables.
- Runtime logs must include request correlation and incident fingerprint data.

## Open questions

- See [OQ-104](../90-open-questions.md#oq-104) for state placement of dedupe and rate limits.
- See [OQ-106](../90-open-questions.md#oq-106) for Jira escalation thresholds relative to Slack and Discord.

## Deferred items

- Durable shared state for dedupe and incident history
- Pull-worker runtime variants beyond the default documented path
- Auto-remediation hooks
- Expanded runtime metrics beyond baseline logging
