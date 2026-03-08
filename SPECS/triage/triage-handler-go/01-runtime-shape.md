# Go Receiver Service Runtime Shape

## Intent

Describe how the Go implementation of `triage-handler` should be structured internally as a serverless receiver service.

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

- Define the Go service entrypoint that terminates pushed log events before normalization.
- Define the Go handler execution path from ingress through outbound notification decisions.
- Define the GCP and AWS Go variants as separate template trees while preserving a shared reduced incident model.
- Document where repository enrichment and local replay fit in the Go implementation.

## Contracts

- Variant layout:
  - GCP variant is rooted at `triage/templates/go/gcp` and includes the Cloud Run service binary, `internal/adapters/gcp/`, `internal/adapters/local/`, and shared runtime packages
  - AWS variant is rooted at `triage/templates/go/aws` and includes the Lambda binary or bootstrap entrypoint, `internal/adapters/aws/`, `internal/adapters/local/`, and shared runtime packages
  - each variant omits the other cloud's ingress wiring from the shipped template tree
- Adapter shape:
  - GCP adapter accepts Pub/Sub push through a `chi` HTTP route suitable for Cloud Run
  - AWS adapter accepts CloudWatch Logs subscription events through a Lambda-compatible service entrypoint that invokes the same internal orchestration layer used behind the HTTP routes
  - local adapter replays JSON input from `stdin` or file for validation and, in the GCP variant, may optionally boot the same `chi` router for HTTP smoke testing
- Suggested package boundaries:
  - `cmd/triage-handler/` in the GCP variant boots the `chi` router for Cloud Run ingress and health endpoints
  - `cmd/triage-handler-lambda/` in the AWS variant hosts the Lambda entrypoint and runtime wiring
  - `cmd/triage-handler-local/` hosts replay and local utility entrypoints
  - `internal/config/` for `triage.yaml` and environment loading
  - `internal/adapters/<selected-cloud>/` plus `internal/adapters/local/`
  - `internal/http/` for shared routes, middleware, and request decoding at the HTTP boundary
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

- The Go implementation is documented as a receiver service with explicit cloud entrypoints.
- The Go handler is shipped as separate GCP and AWS template variants instead of one multi-cloud template tree.
- The Go implementation uses `chi` as a thin HTTP routing layer for Cloud Run and optional local HTTP validation.
- Each Go template variant includes only the ingress adapter for its selected cloud plus shared modules.
- The AWS Lambda entrypoint reuses the shared orchestration flow without depending on the HTTP route table.
- Repository enrichment runs after reduction and before outbound notification.
- Local replay is part of the handler implementation, not a separate tool.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for when durable shared state should replace the MVP per-instance default.

## Deferred items

- Shared worker pools or async queues beyond the baseline synchronous flow
- Additional observability exporters beyond structured logs
