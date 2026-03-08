# Integration Specification: Config Operations
Date: 2026-03-08

## Intent

Define the operator-facing workflow for finding, understanding, and changing `triage` configuration across project config, local CLI state, environment variables, and generated project artifacts.

## Scope

- In scope:
  - operator-facing config discovery commands
  - configuration surface mapping
  - interactive wizard behavior for common changes
  - editability rules for `triage.yaml`
  - effect timing for common configuration changes
- Out of scope:
  - runtime business logic already defined in subsystem specs
  - secret-manager implementation detail
  - arbitrary user-authored YAML outside the documented subset

## Responsibilities

- Define the recommended operator workflow for finding the right configuration surface.
- Map high-frequency changes to the correct file or storage location.
- Document when a change takes effect locally and in deployed runtimes.
- Constrain the YAML edit surface so the CLI can rewrite it deterministically.

## Contracts

- Primary operator commands:
  - `triage config show --project|--local|--effective|--paths`
  - `triage config where <key>`
  - `triage config wizard`
- `triage config show` contract:
  - `--project` reads `./triage.yaml`
  - `--local` reads the local CLI state file and redacts secrets
  - `--effective` shows the merged effective view and labels the source of each displayed field
  - `--paths` prints the absolute paths of `triage.yaml`, the local CLI state file, `.env.example`, and the project `.triage/` directory
- `triage config where <key>` contract:
  - prints the exact key requested
  - prints the scope as `project`, `local`, or `env`
  - prints the physical location where the value lives
  - prints the recommended edit command
  - prints when the change takes effect
- `triage config wizard` contract:
  - is the recommended interactive flow for frequent operator changes
  - must offer these top-level categories:
    - Jira
    - chat routing
    - LLM
    - cloud filter overrides
    - default cloud
  - edits `triage.yaml` for project-scoped keys
  - edits the local CLI state file for local-scoped keys
  - must echo secrets back only in redacted form
- `triage.yaml` automated edit subset:
  - 2-space indentation
  - only mappings and lists from the documented schema
  - no YAML anchors, aliases, or tags
  - no arbitrary multiline block constructs
  - the wizard may rewrite the whole file in canonical order
  - comments are not guaranteed to survive wizard-driven rewrites
- Change matrix:

| Key | Purpose | Scope | Physical location | Recommended command | Takes effect |
| --- | --- | --- | --- | --- | --- |
| `integrations.jira.enabled` | Enable or disable Jira ticket creation | `project` | `./triage.yaml` | `triage config wizard` | Next `triage run` and next deployed runtime after `triage infra apply` |
| `policy.jira_min_severity` | Change the Jira escalation threshold | `project` | `./triage.yaml` | `triage config wizard` | Next `triage run` and next deployed runtime after `triage infra apply` |
| `integrations.routing` | Choose `slack`, `discord`, or `both` | `project` | `./triage.yaml` | `triage config wizard` | Next `triage run` and next deployed runtime after `triage infra apply` |
| `llm.provider` | Select the project LLM provider default | `project` | `./triage.yaml` | `triage config wizard` | Next `triage run` and next deployed runtime after `triage infra apply` |
| `llm.model` | Select the project LLM model default | `project` | `./triage.yaml` | `triage config wizard` | Next `triage run` and next deployed runtime after `triage infra apply` |
| `llm.api_key` | Store the raw LLM API token for the local operator | `local` | `~/.triage/config.json` or `%APPDATA%/triage/config.json` | `triage settings set llm.api_key <value>` or `triage config wizard` | Next command that needs bootstrap completion or LLM-backed execution |
| `default_cloud` | Set the local operator default cloud | `local` | `~/.triage/config.json` or `%APPDATA%/triage/config.json` | `triage settings set default_cloud <value>` or `triage config wizard` | Next CLI invocation |
| `gcp.log_filter_override` | Replace the derived GCP Logging filter | `project` | `./triage.yaml` | `triage config wizard` | Next `triage infra generate`, `triage infra plan`, or `triage infra apply`; deployed effect after apply |
| `aws.filter_pattern_override` | Replace the derived AWS Logs subscription filter | `project` | `./triage.yaml` | `triage config wizard` | Next `triage infra generate`, `triage infra plan`, or `triage infra apply`; deployed effect after apply |

## Dependencies

- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- CLI local state contract: [../10-runtime/12-cli-state.md](../10-runtime/12-cli-state.md)
- Shared config contract: [30-config.md](30-config.md)
- Notification contract: [32-slack-jira.md](32-slack-jira.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage config` is the recommended operator-facing configuration surface.
- `triage settings` remains the low-level local-state surface.
- Project configuration continues to live in `triage.yaml`.
- Per-user bootstrap state continues to live outside the repository in the local CLI state file.
- Frequent operator changes must be discoverable without reading multiple specs manually.

## Open questions

- See [../90-open-questions.md#oq-107](../90-open-questions.md#oq-107) for when stronger secret-storage backends should replace the documented local token path.

## Deferred items

- Preview diffs before wizard-driven rewrites
- Structured export formats beyond human-readable `config show`
- Bulk environment/profile switching flows
