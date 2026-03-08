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
  - `triage init`
  - `triage settings show`
  - `triage settings set <key> <value>`
  - `triage settings validate --cloud gcp|aws|all`
  - `triage template download`
  - `triage infra generate`
  - `triage infra plan`
  - `triage infra apply`
  - `triage run`
- Bootstrap gating:
  - if no local CLI state exists, only `help`, `version`, and `init` are allowed
  - if local CLI state exists but `bootstrap_complete` is `false`, only `help`, `version`, `init`, `settings show`, `settings set`, and `settings validate` are allowed
  - `template download`, `infra generate`, `infra plan`, `infra apply`, and `run` are blocked until bootstrap is complete
- Shared selection flags:
  - `--cloud gcp|aws`
  - `--runtime go|python`
- Distribution contract:
  - the canonical release bundle contains `triage.pyz`, a Unix launcher named `triage`, and a Windows launcher named `triage.cmd`
  - the preferred invocation on macOS and Linux is `triage <command>` when the launcher and `triage.pyz` are on `PATH`
  - the preferred invocation on Windows is `triage <command>` through `triage.cmd`, with `py triage.pyz <command>` as the fallback form
  - the CLI must remain runnable without `pip`, `pipx`, or third-party package managers
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
  - documented writable keys are `default_cloud`, `llm.provider`, `llm.model`, and `llm.api_key`
  - `llm.api_key` is the public CLI key name and maps to the persisted `llm.api_key_value` field in the local state file
  - `triage settings set llm.api_key <value>` may complete bootstrap without rerunning `triage init`
- Template download contract:
  - `triage template download --cloud gcp|aws --runtime go|python --output /abs/path [--force]`
  - `--output` is mandatory and must be an absolute path
  - if `--output` points to an existing non-empty directory, the command fails unless `--force` is supplied
  - templates are versioned with the CLI release and extracted locally rather than fetched ad hoc
  - the downloaded Go template root must include `README.md`, `.env.example`, `cmd/service/`, `cmd/local/`, `internal/`, and `sample-events/`
  - the downloaded Python template root must include `README.md`, `.env.example`, `main.py`, `adapters/`, `notifiers/`, and `sample-events/`
- Infrastructure apply contract:
  - `triage infra apply --cloud gcp|aws --runtime go|python --handler-path /abs/path`
  - `--handler-path` is required when packaging or building the receiver service for deployment
  - `--handler-path` must be absolute
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
- Override model:
  - flags may override selected config values without redefining the full config schema

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Cross-component design: [../01-system-architecture.md](../01-system-architecture.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Local state contract: [12-cli-state.md](12-cli-state.md)
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
