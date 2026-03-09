# Integration Specification: LLM Providers
Date: 2026-03-08

## Intent

Define the optional LLM analysis contract for OpenIncidents without making the core system dependent on one provider.

## Scope

- In scope:
  - provider selection
  - model selection
  - required result shape
  - payload safety expectations before provider submission
- Out of scope:
  - provider-specific prompt text
  - evaluation infrastructure
  - long-term storage of prompts or responses

## Responsibilities

- Define when LLM analysis is optional and how it fits into the pipeline.
- Keep provider selection separate from the stable core domain model.
- Define where the user-level provider credential lives during the current planning phase.
- Define the required strict JSON output shape.
- Link to the canonical security rules for redaction and payload limits.

## Contracts

- Supported providers in the current plan:
  - `none`
  - `openai`
  - `anthropic`
  - `mock` (CLI local testing only; not a production runtime provider)
- Model selection remains free-form and user-provided.
- Provider bootstrap contract:
  - `triage init` requires the user to choose `none`, `openai`, or `anthropic`
  - if the provider is `openai` or `anthropic`, the user must provide both a model and an API token
  - raw provider tokens are persisted only in the per-user CLI local state file documented in [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
  - `triage.yaml` may reference an environment-variable name for runtime wiring, but it must never store the raw API token
- Required result contract: `LLMResult`
  - `summary`
  - `suspected_cause`
  - `suggested_fix`
  - `confidence`
  - `safe_to_escalate`
- Local contract pipeline:
  - `llm-prep.v1` is the normalized and redacted incident-preparation payload emitted by `triage llm-prep`
  - `llm-request.v1` is the provider-ready request contract emitted by `triage llm-request`
  - `llm-analysis.v1` is the analysis result contract emitted by `triage llm-client`
- Default model resolution for `llm-request`:
  - `--model` flag
  - provider-specific env: `TRIAGE_OPENAI_MODEL` or `TRIAGE_ANTHROPIC_MODEL`
  - environment variable `TRIAGE_LLM_MODEL` (or custom `--model-env-var`)
  - project `llm.model` when provider matches
  - provider default (`openai: gpt-4o-mini`)
- `llm-resolve` provider resolution when `--provider` is omitted:
  - `openai` when `OPENAI_API_KEY` exists
  - else `anthropic` when `ANTHROPIC_API_KEY` exists
  - else `mock`
  - when both keys exist, prefer `openai`
- Repository context sources for `llm-prep`:
  - explicit `--repo-url` flags
  - environment variable `TRIAGE_REPO_URLS` (JSON array or comma/newline-separated)
  - `triage.yaml` `repos[].git_url`, with optional `repos[].auth` env indirection
  - context budget presets through `--cost-profile` (`custom`, `lean`, `balanced`, `deep`)
- Required `llm-prep.v1` incident fields:
  - `incident_id`
  - `cloud`
  - `runtime_hint`
  - `service`
  - `severity`
  - `count`
  - `window.first_seen`
  - `window.last_seen`
  - `incident_summary`
  - `error_message`
  - `stacktrace_excerpt`
  - `evidence[]`
  - `repo_context[]`
  - `analysis_mode`
- Required `llm-request.v1` fields:
  - `provider`
  - `model`
  - `incidents[]` (carrying the required `llm-prep.v1` incident subset)
  - `constraints.max_tokens`
  - `response_contract.required_fields`
- Required `llm-analysis.v1` per-incident `analysis` fields:
  - `summary`
  - `suspected_cause`
  - `suggested_fix`
  - `confidence`
  - `safe_to_escalate`
  - `files_or_area_to_check`
  - `tests_to_run`
- Safety constraints:
  - redact email addresses before provider submission
  - redact `Authorization`, `Proxy-Authorization`, `Cookie`, and `Set-Cookie` header values before provider submission
  - redact obvious credential-bearing key/value pairs that use names such as `token`, `secret`, `password`, `api_key`, `access_key`, or `secret_key`
  - truncate stack traces and payload excerpts to at most 8000 characters before provider submission
  - cap payload size before sending any incident context
  - do not persist provider payloads by default in the MVP

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- CLI local state contract: [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- LLM analysis is optional and never precedes reduction.
- OpenAI and Anthropic are the only named providers in the current MVP documentation.
- The provider and model are selected by the user rather than inferred automatically.
- The raw LLM API token is stored only in the local CLI state file during the current documented phase.
- The result must be strict JSON that can feed downstream notification logic.
- The CLI must support an isolated pre-runtime flow (`llm-prep`, `llm-request`, `llm-client`) plus a one-command wrapper (`llm-resolve`) so LLM preparation and analysis can be validated before cloud runtime integration.

## Open questions

- See [OQ-105](../90-open-questions.md#oq-105) for whether the mandatory redaction baseline should expand beyond the documented MVP set.
- See [OQ-107](../90-open-questions.md#oq-107) for the secret-management threshold before production use and for replacing the documented local token store.
- See [OQ-108](../90-open-questions.md#oq-108) for batch strategy and context budgeting when repository snippets are added to LLM payloads.

## Deferred items

- Prompt versioning strategy
- Automatic quality evaluation and provider comparison
- Additional providers and fallback chains
