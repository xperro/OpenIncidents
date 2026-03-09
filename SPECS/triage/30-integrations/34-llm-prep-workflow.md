# Integration Specification: LLM Prep Workflow
Date: 2026-03-09

## Intent

Define the isolated CLI-first workflow that prepares incidents for LLM analysis, including optional repository clone/context enrichment before notifier integration.

## Scope

- In scope:
  - `triage llm-prep`
  - `triage llm-request`
  - `triage llm-client`
  - repository URL resolution and clone/context enrichment for `llm-prep`
  - canonical payload contracts and examples
- Out of scope:
  - notifier delivery
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
- Step 2: `triage llm-request`
  - input schema: `llm-prep.v1`
  - output schema: `llm-request.v1`
  - behavior:
    - choose provider and model
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
