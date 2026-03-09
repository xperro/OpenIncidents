# CLI Specification: `triage`
Date: 2026-03-08

## Intent

Define the user-facing behavior of the `triage` CLI that prepares, validates, deploys, and locally operates OpenIncidents deployments.

## Scope

- In scope:
  - project initialization
  - handler template download
  - infrastructure generation
  - Terraform plan and apply as an official workflow
  - receiver service packaging and deployment for the selected cloud
  - local runtime execution for development and validation
- Out of scope:
  - cloud authentication flows
  - provider-specific infrastructure internals
  - runtime incident processing logic

## Responsibilities

- Scaffold the working structure for an OpenIncidents deployment.
- Bootstrap the local CLI before operational commands are allowed.
- Define the cross-platform distribution and installation shape of the CLI.
- Help operators locate and change project and local configuration without guessing where values live.
- Download official handler templates for the selected cloud and runtime.
- Generate deterministic config and Terraform inputs.
- Validate that required local credentials already exist.
- Package or build the selected receiver service implementation and hand deployment artifacts to infrastructure workflows.
- Run the selected receiver service locally against supported development sources.
- Validate linked repository paths and required local configuration before runtime execution.
- Print clear next steps after generation or infrastructure actions.
- Define the official implementation target for the CLI itself.

## Contracts

- Binary name: `triage`
- Implementation target:
  - the official CLI implementation is Python
  - the CLI uses only Python standard-library modules
  - `argparse` is the required baseline for command wiring, help output, and subcommand structure
  - filesystem, subprocess, environment, HTTP/JSON, and packaging helpers must use the Python standard library unless a future spec explicitly revises that rule
- Command surface:
  - `triage help [command ...]`
  - `triage h [command ...]`
  - `triage init`
  - `triage settings show`
  - `triage settings set <key> <value>`
  - `triage settings validate --cloud gcp|aws|all`
  - `triage config show --project|--local|--effective|--paths`
  - `triage config where <key>`
  - `triage config wizard`
  - `triage template download`
  - `triage infra generate`
  - `triage infra plan`
  - `triage infra apply`
  - `triage run`
- Bootstrap gating:
  - if no local CLI state exists, only `help`, `version`, `init`, `config show`, `config where`, and `config wizard` are allowed
  - if local CLI state exists but `bootstrap_complete` is `false`, only `help`, `version`, `init`, `settings show`, `settings set`, `settings validate`, `config show`, `config where`, and `config wizard` are allowed
  - `template download`, `infra generate`, `infra plan`, `infra apply`, and `run` are blocked until bootstrap is complete
- Help and error behavior:
  - `triage help` and `triage h` print the same top-level help as `triage -h`
  - `triage help <command ...>` prints nested command help, for example `triage help infra apply`
  - invoking a command group without a required subcommand, such as `triage settings` or `triage infra`, prints contextual help for that group and exits non-zero
  - argument parse failures must include a hint telling the operator to rerun the exact command with `-h`
  - user-triggered interrupts during interactive commands must exit cleanly without a Python traceback
- Shared selection flags:
  - `--cloud gcp|aws`
  - `--runtime go|python`
- Distribution contract:
  - the canonical release bundle contains `triage.pyz`, a Unix launcher named `triage`, and a Windows launcher named `triage.cmd`
  - the preferred invocation on macOS and Linux is `triage <command>` when the launcher and `triage.pyz` are on `PATH`
  - the preferred invocation on Windows is `triage <command>` through `triage.cmd`, with `py triage.pyz <command>` as the fallback form
  - the CLI must remain runnable without `pip`, `pipx`, or third-party package managers
  - GitHub Actions is the canonical automation path for CI validation and publishing GitHub Release assets as defined in [13-cli-release.md](13-cli-release.md)
  - macOS may additionally consume the CLI through a Homebrew tap fed by the GitHub Actions release workflow defined in [13-cli-release.md](13-cli-release.md)
- Init contract:
  - `triage init` is interactive and is the required bootstrap entrypoint for the CLI
  - `triage init` asks which cloud to validate now: `gcp`, `aws`, or both
  - `triage init` asks which LLM provider to use: `none`, `openai`, or `anthropic`
  - `triage init` asks for the LLM model when the provider is not `none`
  - `triage init` asks for the LLM token when the provider is not `none`
  - `triage init` writes per-user state into the local CLI state file defined in [12-cli-state.md](12-cli-state.md)
  - `triage init` succeeds only when at least one cloud validates successfully, an LLM provider is chosen explicitly, and a token exists if the provider is not `none`
- Settings contract:
  - `triage settings show` prints the current local CLI state with secret values redacted in human-facing output
  - `triage settings set <key> <value>` mutates only the local CLI state file
  - documented writable keys are `default_cloud`, `jira.issue_type_default`, `llm.provider`, `llm.model`, and `llm.api_key`
  - `llm.api_key` is the public CLI key name and maps to the persisted `llm.api_key_value` field in the local state file
  - `jira.issue_type_default` is the local default used when new or rewritten project config does not yet declare `integrations.jira.issue_type`
  - `triage settings set llm.api_key <value>` may complete bootstrap without rerunning `triage init`
- Configuration discovery contract:
  - `triage config` is the operator-friendly configuration surface
  - `triage settings` remains the low-level surface for direct local state mutation
  - `triage config show --project` renders the project configuration from `./triage.yaml`
  - `triage config show --local` renders the local CLI state with secrets redacted
  - `triage config show --effective` renders the merged effective view with secrets redacted and source labels for each displayed field
  - `triage config show --paths` prints the absolute paths for `triage.yaml`, the local CLI state file, `.env.example`, and the project `.triage/` directory
  - `triage config where <key>` prints the key scope, physical location, recommended edit command, and when the change takes effect
  - `triage config wizard` is the interactive reconfiguration flow for common operator changes
  - the top-level `triage config wizard` categories must include Jira, chat routing, LLM, cloud filter overrides, and default cloud
  - `triage config wizard` edits `triage.yaml` for project-scoped keys and the local CLI state file for local-scoped keys
  - when the Jira project block is created or rewritten without an explicit issue type, `triage config wizard` must materialize `integrations.jira.issue_type` from local `jira.issue_type_default`, defaulting that local value to `Bug` when absent
  - `triage config wizard` may be used before bootstrap completes
- Project config editability contract:
  - `triage.yaml` remains YAML
  - the wizard only supports the canonical YAML shape generated by `triage`
  - the supported YAML subset uses 2-space indentation and only the documented schema structure
  - YAML anchors, aliases, tags, and arbitrary multiline block constructs are out of scope for automated edits
  - the wizard may rewrite the entire file in canonical key order
  - comments in `triage.yaml` are not guaranteed to be preserved after wizard-driven edits
- Template download contract:
  - `triage template download --cloud gcp|aws --runtime go|python --output /abs/path [--force]`
  - `--output` is mandatory and must be an absolute path
  - if `--output` points to an existing non-empty directory, the command fails unless `--force` is supplied
  - templates are versioned with the CLI release and copied from the canonical `triage/templates/` source tree rather than generated ad hoc
  - the canonical source tree is `triage/templates/<runtime>/<cloud>` inside the CLI source tree
  - release bundles must preserve those templates as embedded CLI resources inside `triage.pyz`
  - the CLI must treat `triage/templates/` as the only source of truth for handler template contents
  - `--cloud` selects one of two official cloud-specific handler variants for the chosen runtime: GCP or AWS
  - the downloaded Go template root must be copied from either `triage/templates/go/gcp` or `triage/templates/go/aws`
  - the downloaded Go GCP template root must include `README.md`, `.env.example`, `go.mod`, `go.sum`, `cmd/triage-handler/`, `cmd/triage-handler-local/`, `internal/`, and `sample-events/`
  - the downloaded Go AWS template root must include `README.md`, `.env.example`, `go.mod`, `go.sum`, `cmd/triage-handler-lambda/`, `cmd/triage-handler-local/`, `internal/`, and `sample-events/`
  - the downloaded Python template root must be copied from either `triage/templates/python/gcp` or `triage/templates/python/aws`
  - the downloaded Python GCP template root must include `README.md`, `.env.example`, `requirements.txt`, `main.py`, `app.py`, `adapters/`, `notifiers/`, shared runtime modules, and `sample-events/`
  - the downloaded Python AWS template root must include `README.md`, `.env.example`, `requirements.txt`, `main.py`, `lambda_entrypoint.py`, `adapters/`, `notifiers/`, shared runtime modules, and `sample-events/`
  - template copy must preserve the source tree exactly except for filtering junk files such as `__pycache__`, `.pytest_cache`, `.DS_Store`, `.git`, and `*.pyc`
- Infrastructure apply contract:
  - `triage infra apply --cloud gcp|aws --runtime go|python --handler-path /abs/path`
  - `--handler-path` is required when packaging or building the receiver service for deployment
  - `--handler-path` must be absolute
  - for the GCP path, `triage infra apply` first bootstraps Artifact Registry, then builds and publishes the selected handler image, and finally runs the full Terraform apply with the resolved `container_image`
  - for the Go GCP runtime, `--handler-path` must contain `go.mod`, `go.sum`, and `cmd/triage-handler/`
  - for the Go AWS runtime, `--handler-path` must contain `go.mod`, `go.sum`, and `cmd/triage-handler-lambda/`
  - for the Python GCP runtime, `--handler-path` must contain `requirements.txt`, `main.py`, and `app.py`
  - for the Python AWS runtime, `--handler-path` must contain `requirements.txt`, `main.py`, and `lambda_entrypoint.py`
- Credential model:
  - GCP uses local Application Default Credentials
  - GCP relies on locally available `gcloud` and `terraform`
  - AWS uses local CLI credentials, profiles, or environment variables
  - AWS relies on locally available `aws` and `terraform`
  - the CLI does not implement login flows
  - `infra generate`, `infra plan`, `infra apply`, and `run` must revalidate live credentials and required binaries at execution time rather than trusting an older `init` result
- Validation contract:
  - GCP validation requires `gcloud`, `terraform`, and resolvable Application Default Credentials
  - AWS validation requires `aws`, `terraform`, and a successful `aws sts get-caller-identity`
  - `llm.provider: none` is a valid bootstrap choice and does not require a token
- Expected generated artifacts:
  - `triage.yaml`
  - cloud-specific Terraform inputs
  - receiver service deployment artifacts or references required by the chosen cloud
  - a predictable project scaffold for later implementation work
- Scaffold contract:
  - `triage init` creates this baseline in the current working directory:

```text
.
├── triage.yaml
├── .env.example
├── .gitignore
└── .triage/
    ├── infra/
    ├── build/
    └── cache/
        └── repos/
```

  - `.triage/infra/<cloud>/` is populated by `triage infra generate`
  - `.triage/build/<cloud>/<runtime>/` is populated by `triage infra apply`
  - `.triage/cache/repos/` is created lazily when local repo enrichment or local runtime flows need repository checkout/cache state
- Local run prerequisites:
  - `.env` may be used for local development secrets and must stay untracked
  - configured repository Git URLs and credential env vars must be resolvable for context enrichment
  - when `triage run` uses the default `--input -`, the operator must pipe a replay payload on stdin; if stdin is interactive, the CLI fails fast with guidance instead of blocking silently
- Override model:
  - flags may override selected config values without redefining the full config schema

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Cross-component design: [../01-system-architecture.md](../01-system-architecture.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Config operations guide: [../30-integrations/33-config-operations.md](../30-integrations/33-config-operations.md)
- Local state contract: [12-cli-state.md](12-cli-state.md)
- Release automation contract: [13-cli-release.md](13-cli-release.md)
- Infra contracts: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md), [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage` remains the CLI name.
- `triage init` is a required bootstrap step before operational commands.
- The CLI relies on locally available cloud credentials and fails fast when they are missing.
- `infra generate`, `infra plan`, and `infra apply` remain part of the official CLI workflow rather than convenience-only wrappers.
- `template download` requires an explicit absolute output path and never defaults to a relative destination.
- `triage` supports both GCP and AWS plus official Go and Python handler templates in the MVP documentation.
- The official implementation of `triage` is Python using only the standard library.
- `argparse` is the baseline command framework for the documented CLI path.
- `triage config` is the recommended operator surface for finding and changing configuration.
- `triage settings` remains the low-level local-state surface.
- Per-user CLI bootstrap state lives outside the repo in the local JSON state file.
- Generated outputs must be deterministic and idempotent from the same inputs.
- The CLI keeps both generation and local-run responsibilities in scope for the MVP documentation.

## Open questions

- See [OQ-104](../90-open-questions.md#oq-104) for when the MVP should move from per-instance in-memory dedupe and rate limits to durable shared state.
- See [OQ-107](../90-open-questions.md#oq-107) for when secret-store references should replace the documented local token storage and environment-variable path.

## Deferred items

- Richer interactive UX and guided setup
- Additional scaffolds beyond the initial documented OpenIncidents layout
- Non-Terraform deployment backends
