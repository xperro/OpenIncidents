# Integration Specification: `triage.yaml`
Date: 2026-03-08

## Intent

Define the canonical configuration file and precedence rules that drive OpenIncidents behavior across runtime and infrastructure workflows.

## Scope

- In scope:
  - shared configuration schema
  - policy controls for runtime behavior
  - cloud and environment targeting
  - CLI override boundaries
- Out of scope:
  - secret storage internals
  - provider-specific prompt content
  - notification rendering details

## Responsibilities

- Provide one human-editable configuration entrypoint for the planned toolkit.
- Define which values live in config versus environment variables.
- Define precedence between config, flags, and runtime defaults.
- Keep shared policy values out of component-specific ad hoc files.

## Contracts

- Canonical config file: `triage.yaml`
- MVP schema:

```yaml
cloud: gcp|aws
env: dev|stg|prod|<string>

policy:
  severity_min: WARNING|ERROR|CRITICAL
  window_seconds: 300
  dedupe: true
  max_llm_tokens: 2000
  rate_limit_per_service_per_min: 6

llm:
  provider: none|openai|anthropic
  model: <string>
  api_key_env: <ENV_VAR>

integrations:
  slack:
    enabled: true
    webhook_env: SLACK_WEBHOOK_URL
  jira:
    enabled: true
    base_url: https://example.atlassian.net
    project_key: ABC
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

- Precedence model:
  - CLI flags override `triage.yaml`
  - `triage.yaml` overrides tool defaults
  - environment variables satisfy secret references declared in config
- Validation rules:
  - LLM fields must be complete when `llm.provider` is not `none`
  - Slack and Jira env references must be resolvable when those integrations are enabled

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- LLM contract: [31-llm.md](31-llm.md)
- Notification contract: [32-slack-jira.md](32-slack-jira.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage.yaml` is the shared configuration entrypoint.
- Policy defaults include a 300-second aggregation window and dedupe enabled.
- CLI overrides remain limited to selected operational fields rather than replacing the full config model.
- Secret values are referenced through environment variable names, not embedded directly in the file.

## Open questions

- See [OQ-104](../90-open-questions.md#oq-104) for the final location of dedupe and rate-limit state.
- See [OQ-107](../90-open-questions.md#oq-107) for when secret-store references should replace the current MVP expectation.
- See [OQ-108](../90-open-questions.md#oq-108) for whether CLI Terraform execution remains part of the primary UX.

## Deferred items

- Environment-specific config overlays
- Schema versioning and migration rules
- Secret-store-specific reference types
