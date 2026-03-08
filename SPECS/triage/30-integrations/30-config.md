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
- Define how project configuration differs from persistent local CLI state.
- Define precedence between config, flags, and runtime defaults.
- Keep shared policy values out of component-specific ad hoc files.

## Contracts

- Canonical config file: `triage.yaml`
- Development secret source: local `.env` file (must remain untracked)
- Local CLI bootstrap state: per-user JSON file documented in [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
- MVP schema:

```yaml
cloud: gcp|aws
env: dev|stg|prod|<string>
repos:
  - name: payments-orchestrator
    git_url: https://github.com/example/payments-orchestrator.git
    auth:
      username_env: GIT_USERNAME
      token_env: GIT_TOKEN
    local_path: .triage/repos/payments-orchestrator
    branch: main

policy:
  severity_min: DEBUG|INFO|NOTICE|WARNING|ERROR|CRITICAL|ALERT|EMERGENCY
  jira_min_severity: CRITICAL
  window_seconds: 300
  dedupe: true
  max_llm_tokens: 2000
  rate_limit_per_service_per_min: 6

gcp:
  project_id: my-project
  region: us-central1
  sink_name: triage-prod
  topic_name: triage-prod
  subscription_name: triage-prod-push
  cloud_run_service_name: triage-handler
  artifact_registry_repository: triage
  log_filter_override: ""

aws:
  region: us-east-1
  log_group_name: /aws/lambda/my-service
  lambda_name: triage-handler
  package_format: zip
  filter_name: triage-prod
  log_format: json|space_delimited|text
  severity_field: severity
  severity_word_position: 1
  filter_pattern_override: ""

llm:
  provider: none|openai|anthropic
  model: <string>
  api_key_env: <ENV_VAR>

integrations:
  routing: slack|discord|both
  slack:
    enabled: true
    webhook_env: SLACK_WEBHOOK_URL
  discord:
    enabled: false
    webhook_env: DISCORD_WEBHOOK_URL
  jira:
    enabled: true
    base_url: https://example.atlassian.net
    project_key: ABC
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

- Separation of concerns:
  - `triage.yaml` is project configuration and may be versioned
  - the CLI local state file is per-user bootstrap state and must never live inside the repo
  - raw LLM API keys do not belong in `triage.yaml`
  - `llm.api_key_env` is only an environment-variable reference for runtime wiring, not the secret value itself
- Precedence model:
  - CLI flags override `triage.yaml`
  - `triage.yaml` overrides the local CLI state file for project-scoped settings
  - the local CLI state file overrides tool defaults for persistent per-user bootstrap values
  - `.env` provides local development values for environment variables
  - process environment variables satisfy secret references declared in config
- Validation rules:
  - `triage init` and the local CLI state must be complete before `template download`, `infra generate`, `infra plan`, `infra apply`, or `run` may execute
  - exactly one cloud path is active per deployment because `cloud` selects either `gcp` or `aws`
  - the selected cloud block must be complete for `infra generate`, `infra plan`, and `infra apply`
  - `policy.severity_min` follows the normalized GCP severity scale documented in the official [Google Cloud LogSeverity reference](https://cloud.google.com/logging/docs/reference/v2/rpc/google.logging.type#logseverity)
  - `policy.jira_min_severity` follows the same normalized severity scale and defaults to `CRITICAL`
  - when `cloud: aws`, `log_format` must be one of `json`, `space_delimited`, or `text`
  - `severity_field` is required when AWS `log_format` is `json`
  - `severity_word_position` is required when AWS `log_format` is `space_delimited`
  - LLM fields must be complete when `llm.provider` is not `none`
  - Slack, Discord, and Jira env references must be resolvable when those integrations are enabled
  - each repository in `repos` must have `git_url` and credential env references resolvable at runtime
  - `local_path` is optional but recommended to avoid repeated clones and reduce token usage through bounded context extraction
- Filter derivation rules:
  - GCP derives `log_filter` as `severity>=X` from `policy.severity_min` unless `gcp.log_filter_override` is set
  - AWS `json` derives `filter_pattern` from the configured `severity_field` unless `aws.filter_pattern_override` is set
  - AWS `space_delimited` derives `filter_pattern` from `severity_word_position` unless `aws.filter_pattern_override` is set
  - AWS `text` uses a broad subscription and applies severity filtering in the runtime unless `aws.filter_pattern_override` is set

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- CLI local state contract: [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- LLM contract: [31-llm.md](31-llm.md)
- Notification contract: [32-slack-jira.md](32-slack-jira.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage.yaml` is the shared configuration entrypoint.
- `triage.yaml` does not replace the per-user CLI state file.
- Policy defaults include a 300-second aggregation window and dedupe enabled.
- Policy defaults include `jira_min_severity: CRITICAL`.
- The shared severity threshold uses the normalized `DEBUG` through `EMERGENCY` scale.
- CLI overrides remain limited to selected operational fields rather than replacing the full config model.
- Secret values are referenced through environment variable names, not embedded directly in the file.
- Local `.env` is allowed for MVP development and must be excluded from version control.
- Repository integration uses Git URL + credentials, with optional local cache paths for efficiency.
- Notification routing is explicit through `integrations.routing` with support for `slack`, `discord`, or `both`.
- Jira remains separately configurable as an escalation target rather than a chat-routing destination.
- MVP dedupe and rate limits are best-effort per warm runtime instance rather than globally coordinated across instances.

## Open questions

- See [OQ-104](../90-open-questions.md#oq-104) for when durable shared state should replace the MVP per-instance default.
- See [OQ-107](../90-open-questions.md#oq-107) for when secret-store references should replace the current MVP expectation for local CLI token storage and runtime environment wiring.
- See [OQ-106](../90-open-questions.md#oq-106) for when Jira escalation should expand beyond the baseline severity threshold.

## Deferred items

- Environment-specific config overlays
- Schema versioning and migration rules
- Secret-store-specific reference types
