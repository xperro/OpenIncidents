# Runtime Specification: CLI Local State
Date: 2026-03-08

## Intent

Define the per-user persistent local state that `triage` uses for bootstrap completion, default selections, and local secret storage outside the project repository.

## Scope

- In scope:
  - local state file location by operating system
  - persisted bootstrap fields and JSON shape
  - lifecycle rules for `init`, `settings set`, and `settings validate`
  - best-effort local file protection expectations
- Out of scope:
  - project-level runtime configuration in `triage.yaml`
  - cloud secret manager implementation detail
  - OS keychain integration

## Responsibilities

- Define where the CLI stores persistent per-user state.
- Separate user-local bootstrap data from versionable project configuration.
- Define how bootstrap completion is computed and recomputed.
- Define how `triage` updates state after interactive setup or later settings changes.
- Define how operators discover the local state path without confusing it with the project `.triage/` directory.

## Contracts

- Storage format:
  - JSON
  - one file per local user profile
  - the file lives outside the repository and must not be committed or copied into project scaffolds
- Storage path:
  - Windows: `%APPDATA%/triage/config.json`
  - macOS: `~/.triage/config.json`
  - Linux: `~/.triage/config.json`
- Path distinction:
  - `~/.triage/` or `%APPDATA%/triage/` is the per-user local CLI home
  - `./.triage/` inside a project directory is the generated project workspace
  - the two locations are intentionally separate and must not be conflated
- Minimum persisted shape:

```json
{
  "schema_version": 1,
  "bootstrap_complete": false,
  "default_cloud": "gcp",
  "clouds": {
    "gcp": {
      "enabled": true
    },
    "aws": {
      "enabled": false
    }
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1",
    "api_key_env": "OPENAI_API_KEY",
    "api_key_value": "<secret>"
  }
}
```

- Field rules:
  - `schema_version` starts at `1`
  - `bootstrap_complete` is derived state and must reflect whether the minimum bootstrap contract is currently satisfied
  - `default_cloud` may be `gcp`, `aws`, or absent until a selection is made
  - `clouds.gcp.enabled` and `clouds.aws.enabled` represent the latest successful live validation result for each cloud
  - `llm.provider` must be one of `none`, `openai`, or `anthropic`
  - `llm.model` is required when `llm.provider` is not `none`
  - `llm.api_key_env` defaults to `OPENAI_API_KEY` for OpenAI and `ANTHROPIC_API_KEY` for Anthropic
  - `llm.api_key_value` stores the raw user token only in this local state file during the current documented phase
- Lifecycle rules:
  - if the state file does not exist, `triage` is considered not initialized
  - `triage init` creates the state file and may leave it partial if the bootstrap flow does not complete
  - `triage settings set <key> <value>` updates only the local state file
  - the public CLI key `llm.api_key` maps to the persisted field `llm.api_key_value`
  - `triage config show --local` reads from this file and must redact secret values in human-facing output
  - `triage config where llm.api_key` resolves to this file
  - `triage config wizard` mutates this file when the selected key is local-scoped
  - `triage settings validate --cloud gcp|aws|all` reruns live credential and tooling checks, updates cloud validation results, and recomputes `bootstrap_complete`
  - `bootstrap_complete` becomes `true` only when at least one cloud has validated successfully, an LLM provider has been chosen explicitly, and a token exists if the provider is not `none`
- File protection baseline:
  - create the state file with best-effort restrictive permissions
  - on Unix-like systems, the target mode is owner-read and owner-write only
  - on Windows, use best-effort current-user-only placement and avoid broader shared locations

## Dependencies

- CLI contract: [10-cli.md](10-cli.md)
- Shared config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Config operations guide: [../30-integrations/33-config-operations.md](../30-integrations/33-config-operations.md)
- LLM contract: [../30-integrations/31-llm.md](../30-integrations/31-llm.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage` keeps bootstrap state in a per-user JSON file rather than in `triage.yaml`.
- The local state file is the documented persistence location for the raw LLM token during the current phase.
- `bootstrap_complete` is recomputed after `init`, `settings set`, and `settings validate`.
- The local CLI home uses `~/.triage/` on Unix-like systems and `%APPDATA%/triage/` on Windows for operator discoverability.
- The local state file is cross-platform and must not depend on third-party Python packages.

## Open questions

- See [../90-open-questions.md#oq-107](../90-open-questions.md#oq-107) for when keychains or cloud secret stores should replace the documented local token storage path.

## Deferred items

- OS-native keychain integration
- Multiple named local profiles
- Encrypted local state at rest beyond best-effort filesystem protections
