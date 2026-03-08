# Go Handler Runtime Shape

## Intent

Describe how the Go implementation of `triage-handler` should be structured internally.

## Scope

- In scope:
  - ingress adapters for GCP, AWS, and local replay
  - internal package layout
  - config loading and validation
  - normalization, reduction, enrichment, and observability flow
- Out of scope:
  - notifier payload definitions
  - infra resource definitions

## Responsibilities

- Define the Go handler execution path from ingress through outbound notification decisions.
- Keep GCP and AWS adapters separate while preserving a shared reduced incident model.
- Document where repository enrichment and local replay fit in the Go implementation.

## Contracts

- Adapter shape:
  - GCP adapter accepts Pub/Sub push requests through an HTTP handler suitable for Cloud Run
  - AWS adapter accepts CloudWatch Logs subscription events through a Lambda-compatible handler
  - local adapter replays JSON input from `stdin` or file for validation
- Suggested package boundaries:
  - `cmd/` only for local helper entrypoints if needed
  - `internal/config/` for `triage.yaml` and environment loading
  - `internal/adapters/gcp/`, `internal/adapters/aws/`, and `internal/adapters/local/`
  - `internal/normalize/`, `internal/reduce/`, `internal/enrich/`, `internal/notifiers/`
  - `internal/observability/` for structured logging and request correlation
- Config loading:
  - parse `triage.yaml`
  - resolve environment-backed secrets declared in config
  - validate cloud-specific blocks and repository definitions before runtime work begins
- Processing flow:
  - decode source event
  - normalize to the shared internal incident event
  - apply severity threshold
  - reduce and dedupe
  - enrich from configured repositories
  - optionally invoke LLM
  - route to Slack, Discord, and optionally Jira
- Observability:
  - include request identifiers, cloud source, fingerprint, and repository correlation metadata in logs
  - keep log output structured and machine-parseable

## Dependencies

- Shared runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)

## Locked decisions

- The Go handler keeps ingress adapters separated by cloud.
- Repository enrichment runs after reduction and before outbound notification.
- Local replay is part of the handler implementation, not a separate tool.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for durable dedupe state.

## Deferred items

- Shared worker pools or async queues beyond the baseline synchronous flow
- Additional observability exporters beyond structured logs
