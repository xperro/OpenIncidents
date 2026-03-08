# Python Handler Specification: `triage-handler-python`

## Intent

Describe the Python-specific implementation shape of `triage-handler` while preserving the shared runtime contract defined in [../10-runtime/11-handler.md](../10-runtime/11-handler.md).

## Scope

- In scope:
  - Python implementation detail for GCP, AWS, and local handler entrypoints
  - module-level organization and execution model
  - Slack, Discord, and Jira integration detail for the Python handler
  - packaging and local validation expectations for Python
- Out of scope:
  - redefining the shared incident model
  - redefining `triage.yaml`
  - defining a second CLI surface separate from `triage`

## Responsibilities

- Specialize the shared `triage-handler` contract for Python.
- Define how the Python implementation structures adapters, reduction flow, and notifier clients.
- Document Python-specific build and deployment expectations for Cloud Run and Lambda.
- Stay aligned with the shared config, notification, IAM, and infra contracts.

## Contracts

- Runtime language: Python
- Shared runtime contract source: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Notification contract source: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Standard-library baseline:
  - local helper entrypoints use only Python standard library modules
  - HTTP and JSON handling for Slack, Discord, and Jira use standard-library modules
  - third-party CLI frameworks are not allowed in the documented Python path
- CLI boundary:
  - this folder does not define the `triage` CLI
  - the official CLI remains specified separately in [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
  - Python may expose local helper entrypoints for the handler, but the official `triage` CLI remains documented only in the shared CLI spec

## Dependencies

- Shared runtime: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Shared CLI: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Config: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Notifications: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Infra: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md), [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)

## Locked decisions

- Python is one of the two official handler implementation languages.
- The documented Python path uses standard-library modules for local helper entrypoints and outbound integrations.
- Python does not define a second official `triage` CLI.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for dedupe and rate-limit state placement.
- See [../90-open-questions.md#oq-106](../90-open-questions.md#oq-106) for Jira escalation thresholds.

## Deferred items

- Alternative Python runtime variants beyond the documented standard-library baseline
- Additional packaging optimizations beyond the baseline Cloud Run and Lambda paths
