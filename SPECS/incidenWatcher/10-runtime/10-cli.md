# CLI Specification: `triage`
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the user-facing behavior of the `triage` CLI that prepares, validates, deploys, and locally operates OpenIncidents deployments.

## Scope

- In scope:
  - project initialization
  - handler template download
  - infrastructure generation
  - Terraform plan and apply as an official workflow
  - handler packaging and deployment for the selected cloud
  - local runtime execution for development and validation
- Out of scope:
  - cloud authentication flows
  - provider-specific infrastructure internals
  - runtime incident processing logic

## Responsibilities

- Scaffold the working structure for an OpenIncidents deployment.
- Download official handler templates for the selected cloud and runtime.
- Generate deterministic config and Terraform inputs.
- Validate that required local credentials already exist.
- Package or build the selected handler and hand deployment artifacts to infrastructure workflows.
- Run the handler locally against supported development sources.
- Validate linked repository paths and required local configuration before runtime execution.
- Print clear next steps after generation or infrastructure actions.

## Contracts

- Binary name: `triage`
- Command surface:
  - `triage init`
  - `triage template download`
  - `triage infra generate`
  - `triage infra plan`
  - `triage infra apply`
  - `triage run`
- Shared selection flags:
  - `--cloud gcp|aws`
  - `--runtime go|python`
- Template download contract:
  - `triage template download --cloud gcp|aws --runtime go|python --output /abs/path [--force]`
  - `--output` is mandatory and must be an absolute path
  - if `--output` points to an existing non-empty directory, the command fails unless `--force` is supplied
  - templates are versioned with the CLI release and extracted locally rather than fetched ad hoc
- Infrastructure apply contract:
  - `triage infra apply --cloud gcp|aws --runtime go|python --handler-path /abs/path`
  - `--handler-path` is required when packaging or building the handler for deployment
  - `--handler-path` must be absolute
- Credential model:
  - GCP uses local Application Default Credentials
  - GCP relies on locally available `gcloud` and `terraform`
  - AWS uses local CLI credentials, profiles, or environment variables
  - AWS relies on locally available `aws` and `terraform`
  - the CLI does not implement login flows
- Expected generated artifacts:
  - `triage.yaml`
  - cloud-specific Terraform inputs
  - handler deployment artifacts or references required by the chosen cloud
  - a predictable project scaffold for later implementation work
- Local run prerequisites:
  - `.env` may be used for local development secrets and must stay untracked
  - configured repository Git URLs and credential env vars must be resolvable for context enrichment
- Override model:
  - flags may override selected config values without redefining the full config schema

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Cross-component design: [../01-system-architecture.md](../01-system-architecture.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)
- Infra contracts: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md), [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- `triage` remains the CLI name.
- The CLI relies on locally available cloud credentials and fails fast when they are missing.
- `infra generate`, `infra plan`, and `infra apply` remain part of the official CLI workflow rather than convenience-only wrappers.
- `template download` requires an explicit absolute output path and never defaults to a relative destination.
- `triage` supports both GCP and AWS plus official Go and Python handler templates in the MVP documentation.
- Generated outputs must be deterministic and idempotent from the same inputs.
- The CLI keeps both generation and local-run responsibilities in scope for the MVP documentation.

## Open questions

- See [OQ-104](../90-open-questions.md#oq-104) for the final placement of dedupe and rate-limit state because it affects local parity expectations.
- See [OQ-107](../90-open-questions.md#oq-107) for when secret-store references should replace the documented environment-variable path.

## Deferred items

- Richer interactive UX and guided setup
- Additional scaffolds beyond the initial OpenIncidents layout
- Non-Terraform deployment backends
