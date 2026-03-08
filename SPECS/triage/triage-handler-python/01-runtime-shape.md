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
- Keep GCP and AWS adapters separate while preserving a shared reduced incident model.
- Document where repository enrichment and local replay fit in the Python implementation.

## Contracts

- Adapter shape:
  - GCP adapter accepts Pub/Sub push through an HTTP service endpoint suitable for Cloud Run
  - AWS adapter accepts CloudWatch Logs subscription events through a Lambda-compatible service entrypoint
  - local adapter replays JSON input from `stdin` or file for validation
- Suggested module boundaries:
  - `config/` for `triage.yaml` and environment resolution
  - `adapters/gcp.py`, `adapters/aws.py`, `adapters/local.py`
  - `normalize.py`, `reduce.py`, `enrich.py`, `notifiers/`, `observability.py`
  - `main.py` only for local helper entrypoints and runtime wiring
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
- The Python handler keeps ingress adapters separated by cloud.
- Repository enrichment runs after reduction and before outbound notification.
- Local replay is part of the handler implementation, not a separate product.

## Open questions

- See [../90-open-questions.md#oq-104](../90-open-questions.md#oq-104) for durable dedupe state.

## Deferred items

- Async execution variants beyond the baseline synchronous request flow
- Additional observability exporters beyond structured logs
