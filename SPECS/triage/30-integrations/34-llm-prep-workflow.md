# Integration Specification: LLM Prep Workflow
Date: 2026-03-09

## Intent

Define the isolated CLI-first workflow that prepares incidents for LLM analysis, including optional repository clone/context enrichment before notifier integration.

## Scope

- In scope:
  - `triage llm-prep`
  - `triage llm-request`
  - `triage llm-client`
  - `triage llm-resolve` one-command end-to-end flow
  - `triage notify`
  - repository URL resolution and clone/context enrichment for `llm-prep`
  - canonical payload contracts and examples
- Out of scope:
  - cloud runtime integration details

## Responsibilities

- Provide a deterministic path from raw events to provider-ready LLM requests.
- Keep this flow usable before cloud deployment and before runtime integration.
- Enforce redaction, truncation, and payload shaping prior to provider calls.
- Preserve strict JSON contracts between steps.

## Contracts

- Step 1: `triage llm-prep`
  - input: raw JSON payloads from file or stdin
  - output schema: `llm-prep.v1`
  - behavior:
    - decode cloud envelopes (GCP Pub/Sub, AWS CloudWatch subscription)
    - normalize events
    - apply severity filter (default `ERROR`)
    - dedupe/group events by fingerprint
    - redact sensitive strings
    - truncate context
    - optional repository context enrichment from:
      - `--repo-url` CLI flags
      - environment variable `TRIAGE_REPO_URLS` (JSON array or comma/newline-separated URLs)
      - `triage.yaml` `repos[].git_url`
    - when `triage.yaml repos[].auth` exists, resolve credentials from `username_env` and `token_env` before clone
    - optional context budget profile with `--cost-profile`:
      - `custom`: keeps explicit flag values
      - `lean`: low-cost defaults (`max_incidents=5`, `max_context_chars=1200`, `max_stack_lines=8`, `repo_max_files=1`, `repo_max_snippet_lines=30`)
      - `balanced`: moderate defaults (`10`, `2200`, `12`, `2`, `50`)
      - `deep`: high-context defaults (`20`, `4000`, `20`, `3`, `80`)
    - when `--cost-profile` is omitted, `triage llm-prep` may read the default profile from `TRIAGE_LLM_COST_PROFILE` (or the variable selected by `--cost-profile-env-var`)
    - repository scan excludes common non-business files (for example `mvnw`, lockfiles) and prioritizes business paths (`internal/`, `src/`, `service/`, `repository/`, `handler/`)
- Step 2: `triage llm-request`
  - input schema: `llm-prep.v1`
  - output schema: `llm-request.v1`
  - behavior:
    - choose provider and model
    - choose response language from `TRIAGE_LANGUAGE` (`english` or `spanish`)
    - model resolution order:
      - `--model` (if provided)
      - provider-specific env (`TRIAGE_OPENAI_MODEL` or `TRIAGE_ANTHROPIC_MODEL`)
      - environment variable `TRIAGE_LLM_MODEL` (or the variable selected by `--model-env-var`)
      - project `triage.yaml` `llm.model` when `llm.provider` matches the request provider
      - provider default (`openai: gpt-4o-mini`)
    - enforce per-incident max token budget
    - attach strict response contract
- Step 3: `triage llm-client`
  - input schema: `llm-request.v1`
  - output schema: `llm-analysis.v1`
  - providers:
    - `mock`
    - `openai`
    - `anthropic`
  - behavior:
    - execute one model call per incident
    - parse strict JSON result
    - emit normalized analysis output

## Example Flow

Single-command full flow:

```bash
cat events.json | .venv/bin/python -m triage llm-resolve \
  --cloud gcp \
  --runtime go \
  --provider openai \
  --artifact-dir "$(pwd)/llm-artifacts" \
  --output "$(pwd)/llm-analysis.json"
```

This command persists intermediate artifacts in `artifact-dir`:
- `prepared.json`
- `llm-request.json`
- `llm-analysis.json`
- Provider resolution for `llm-resolve` when `--provider` is omitted:
  - use `openai` when `OPENAI_API_KEY` is present
  - otherwise use `anthropic` when `ANTHROPIC_API_KEY` is present
  - if both keys are present, prefer `openai`
  - if no key is present, fallback to `mock` for a coarse local analysis

Optional notify step:

```bash
.venv/bin/python -m triage notify \
  --input "$(pwd)/llm-analysis.json" \
  --target discord \
  --dry-run
```

Or notify directly from resolve:

```bash
cat events.json | .venv/bin/python -m triage llm-resolve \
  --cloud gcp \
  --runtime go \
  --provider openai \
  --notify \
  --notify-target discord \
  --output "$(pwd)/llm-analysis.json"
```

1. Prepare incidents:

```bash
cat events.json | .venv/bin/python -m triage llm-prep --cloud gcp --runtime go --output "$(pwd)/prepared.json"
```

Optional repository enrichment (example):

```bash
cat events.json | .venv/bin/python -m triage llm-prep \
  --cloud gcp \
  --runtime go \
  --repo-url https://github.com/chrisloarryn/rent-a-car-microservices.git \
  --repo-branch main \
  --output "$(pwd)/prepared-with-repo.json"
```

Low-cost profile (recommended during MVP validation):

```bash
cat events.json | .venv/bin/python -m triage llm-prep \
  --cloud gcp \
  --runtime go \
  --cost-profile lean \
  --output "$(pwd)/prepared-lean.json"
```

Low-cost profile from environment (no profile flag):

```bash
export TRIAGE_LLM_COST_PROFILE=lean
cat events.json | .venv/bin/python -m triage llm-prep \
  --cloud gcp \
  --runtime go \
  --output "$(pwd)/prepared-lean-env.json"
```

2. Build LLM request:

```bash
.venv/bin/python -m triage llm-request \
  --input "$(pwd)/prepared.json" \
  --provider mock \
  --model mock-1 \
  --output "$(pwd)/llm-request.json"
```

3. Execute client:

```bash
.venv/bin/python -m triage llm-client \
  --input "$(pwd)/llm-request.json" \
  --provider mock \
  --output "$(pwd)/llm-analysis.json"
```

## Example `llm-prep.v1` Shape

```json
{
  "schema_version": "llm-prep.v1",
  "request_id": "prep-1234abcd",
  "meta": {
    "input_events": 9,
    "prepared_incidents": 5,
    "severity_min": "ERROR"
  },
  "incidents": [
    {
      "incident_id": "9c65f1b97f392153",
      "service": "approve-mrs",
      "severity": "ERROR",
      "incident_summary": "db timeout on postgres while fetching merge requests",
      "llm_input": {
        "incident_summary": "db timeout on postgres while fetching merge requests",
        "evidence": ["...redacted event excerpt..."],
        "constraints": {
          "max_tokens": 1200,
          "redaction_applied": true
        }
      },
      "repo_context": [],
      "analysis_mode": "pre_repo"
    }
  ]
}
```

## Example `llm-request.v1` Shape

```json
{
  "schema_version": "llm-request.v1",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "incidents": [
    {
      "incident_id": "9c65f1b97f392153",
      "incident_summary": "db timeout on postgres while fetching merge requests",
      "evidence": ["...redacted event excerpt..."],
      "constraints": {
        "max_tokens": 1200,
        "redaction_applied": true
      },
      "response_contract": {
        "format": "json",
        "required_fields": [
          "summary",
          "suspected_cause",
          "suggested_fix",
          "confidence",
          "safe_to_escalate",
          "files_or_area_to_check",
          "tests_to_run"
        ]
      }
    }
  ]
}
```

## Example `llm-analysis.v1` Shape

```json
{
  "schema_version": "llm-analysis.v1",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "results": [
    {
      "incident_id": "9c65f1b97f392153",
      "analysis": {
        "summary": "Database timeout on merge-request read path.",
        "suspected_cause": "Slow query or saturated postgres connection pool.",
        "suggested_fix": "Optimize query and increase pool limits with timeout guard.",
        "confidence": 0.71,
        "safe_to_escalate": true,
        "files_or_area_to_check": ["internal/approvals/repository.go"],
        "tests_to_run": ["unit", "integration"]
      }
    }
  ]
}
```

## Dependencies

- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- LLM contract: [31-llm.md](31-llm.md)
- Config contract: [30-config.md](30-config.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- The isolated LLM workflow is CLI-first and can run before cloud runtime integration.
- Payload contracts are versioned as `llm-prep.v1`, `llm-request.v1`, and `llm-analysis.v1`.
- One model call per incident is the current default.
- `repo_context` is optional and populated when repository sources are configured.
- Repository sources may come from flags, env, or `triage.yaml`, with CLI flags treated as additive.

## Open questions

- See [OQ-108](../90-open-questions.md#oq-108) for batching strategy once repository snippets are added.

## Deferred items

- Notifier integration with LLM analysis results
- Adaptive batching and dynamic token-budgeting policies
