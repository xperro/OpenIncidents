# Python Receiver Service Runtime Shape

## Intent

Describe how the Python implementation of `triage-handler` should be structured internally as a serverless receiver service.

## Scope

- In scope:
  - ingress adapters for GCP, AWS, and local replay
  - module layout
  - config loading and validation
  - normalization, reduction, enrichment, and observability flow
- Out of scope:
  - notifier payload definitions
  - infra resource definitions

## Responsibilities

- Define the Python service entrypoint that terminates pushed log events before normalization.
- Define the Python handler execution path from ingress through outbound notification decisions.
- Define the GCP and AWS Python variants as separate template trees while preserving a shared reduced incident model.
- Document where repository enrichment and local replay fit in the Python implementation.

## Contracts

- Variant layout:
  - GCP variant is rooted at `triage/templates/python/gcp` and includes the Cloud Run HTTP app, `adapters/gcp.py`, `adapters/local.py`, and shared runtime modules
  - AWS variant is rooted at `triage/templates/python/aws` and includes the Lambda entrypoint, `adapters/aws.py`, `adapters/local.py`, and shared runtime modules
  - each variant omits the other cloud's ingress wiring from the shipped template tree
- Adapter shape:
  - GCP adapter accepts Pub/Sub push through a `Starlette` HTTP route suitable for Cloud Run
  - AWS adapter accepts CloudWatch Logs subscription events through a Lambda-compatible service entrypoint that invokes the same internal orchestration layer used behind the HTTP routes
  - local adapter replays JSON input from `stdin` or file for validation and, in the GCP variant, may optionally boot the same `Starlette` app for HTTP smoke testing
- Suggested module boundaries:
  - `app.py` in the GCP variant for `Starlette` routes, health endpoints, and Cloud Run wiring
  - `lambda_entrypoint.py` in the AWS variant for Lambda event decoding and runtime wiring
  - `config/` for `triage.yaml` and environment resolution
  - `adapters/<selected-cloud>.py` plus `adapters/local.py`
  - `normalize.py`, `reduce.py`, `enrich.py`, `notifiers/`, `observability.py`
  - `main.py` only for local helper entrypoints and non-HTTP runtime wiring
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
  - keep output structured and suitable for cloud log parsing

## Dependencies

- Shared runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)

## Locked decisions

- The Python implementation is documented as a receiver service with explicit cloud entrypoints.
- The Python handler is shipped as separate GCP and AWS template variants instead of one multi-cloud template tree.
- The Python implementation uses `Starlette` as a thin HTTP routing layer for Cloud Run and optional local HTTP validation.
- Each Python template variant includes only the ingress adapter for its selected cloud plus shared modules.
- The AWS Lambda entrypoint reuses the shared orchestration flow without depending on the HTTP route table.
- Repository enrichment runs after reduction and before outbound notification.
- Local replay is part of the handler implementation, not a separate product.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for when durable shared state should replace the MVP per-instance default.

## Deferred items

- Async execution variants beyond the baseline synchronous request flow
- Additional observability exporters beyond structured logs
