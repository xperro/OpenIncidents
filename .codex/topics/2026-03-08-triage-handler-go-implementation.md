# 2026-03-08 - triage-handler-go implementation

## Context

- Work topic: initial implementation of `triage-handler-go`
- Canonical policy source: [../../AGENTS.md](../../AGENTS.md)
- Canonical specs:
  - [../../SPECS/triage/README.md](../../SPECS/triage/README.md)
  - [../../SPECS/triage/10-runtime/11-handler.md](../../SPECS/triage/10-runtime/11-handler.md)
  - [../../SPECS/triage/triage-handler-go/README.md](../../SPECS/triage/triage-handler-go/README.md)
  - [../../SPECS/triage/triage-handler-go/01-runtime-shape.md](../../SPECS/triage/triage-handler-go/01-runtime-shape.md)
  - [../../SPECS/triage/triage-handler-go/02-integrations.md](../../SPECS/triage/triage-handler-go/02-integrations.md)
  - [../../SPECS/triage/triage-handler-go/03-packaging-and-local.md](../../SPECS/triage/triage-handler-go/03-packaging-and-local.md)
  - [../../SPECS/triage/30-integrations/30-config.md](../../SPECS/triage/30-integrations/30-config.md)
  - [../../SPECS/triage/30-integrations/32-slack-jira.md](../../SPECS/triage/30-integrations/32-slack-jira.md)

## AGENTS.md constraints applied

- Started from the spec set before writing code.
- Kept naming stable: `OpenIncidents`, `triage`, `triage-handler`.
- Focused only on the Go handler runtime in this work topic.
- Avoided changing unrelated untracked work already present in the repo.

## Implemented scope

- New Go module under `triage-handler-go/`
- Cloud Run HTTP receiver for GCP Pub/Sub push
- Lambda entrypoint for AWS CloudWatch Logs subscriptions
- Local replay entrypoint for `stdin` or file input
- Shared processing pipeline:
  - config loading from `triage.yaml` plus `.env`
  - normalization for GCP and AWS payloads
  - severity thresholding
  - in-memory dedupe and per-service rate limiting
  - local-path repository enrichment
  - Slack, Discord, and Jira outbound delivery
- Tests for:
  - GCP and AWS payload handling
  - reducer dedupe behavior
  - notifier delivery

## Known limitations left explicit

- LLM providers are wired as an interface, but OpenAI and Anthropic calls are not implemented yet.
- Repository enrichment currently searches configured local paths only; remote clone/pull behavior is not implemented yet.
- Dedupe and rate-limit state remain in-memory and per-instance, matching the current MVP spec.
