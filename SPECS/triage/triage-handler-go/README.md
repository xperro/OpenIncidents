# Go Receiver Service Specification: `triage-handler-go`

## Intent

Describe the Go-specific implementation shape of `triage-handler` as a serverless receiver service while preserving the shared runtime contract defined in [../10-runtime/11-handler.md](../10-runtime/11-handler.md).

## Scope

- In scope:
  - Go implementation detail for GCP and AWS receiver service entrypoints plus local replay
  - package-level organization and execution model
  - Slack, Discord, and Jira integration detail for the Go receiver service
  - packaging and local validation expectations for Go
- Out of scope:
  - redefining the shared incident model
  - redefining `triage.yaml`
  - defining a second CLI surface separate from `triage`

## Responsibilities

- Specialize the shared `triage-handler` contract for Go.
- Define how the Go implementation structures adapters, reduction flow, and notifier clients.
- Document Go-specific build and deployment expectations for the serverless receiver service on Cloud Run and Lambda.
- Stay aligned with the shared config, notification, IAM, and infra contracts.

## Contracts

- Runtime language: Go
- Shared runtime contract source: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Notification contract source: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Service role:
  - the Go implementation represents a serverless receiver service for pushed log events
  - on GCP it exposes the Cloud Run HTTP endpoint
  - on AWS it exposes the Lambda runtime entrypoint
- HTTP client baseline:
  - the Go handler uses `net/http` as the base client for Slack, Discord, and Jira
  - JSON encoding and decoding use the Go standard library
- CLI boundary:
  - this folder does not define the `triage` CLI
  - the official CLI remains specified separately in [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
  - the official CLI is implemented in Python and does not change the Go handler internals

## Dependencies

- Shared runtime: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Shared CLI: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Config: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Notifications: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Infra: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md), [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)

## Locked decisions

- Go is one of the two official handler implementation languages.
- The Go implementation represents the deployed receiver service, not just an internal callback.
- Go-specific handler HTTP integrations use `net/http`.
- Go-specific handler detail belongs here instead of expanding the shared runtime spec.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for dedupe and rate-limit state placement.
- See [../90-open-questions.md#oq-106](../90-open-questions.md#oq-106) for Jira escalation thresholds.

## Deferred items

- Alternative HTTP client abstractions beyond the standard library
- Additional Go-specific deployment variants beyond the documented Cloud Run and Lambda paths
