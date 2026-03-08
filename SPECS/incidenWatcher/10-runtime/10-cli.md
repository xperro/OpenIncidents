# CLI Specification: `triage`
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the user-facing behavior of the `triage` CLI that prepares, validates, and optionally operates OpenIncidents deployments.

## Scope

- In scope:
  - project initialization
  - infrastructure generation
  - optional Terraform plan and apply helpers
  - local runtime execution for development and validation
- Out of scope:
  - cloud authentication flows
  - provider-specific infrastructure internals
  - runtime incident processing logic

## Responsibilities

- Scaffold the working structure for an OpenIncidents deployment.
- Generate deterministic config and Terraform inputs.
- Validate that required local credentials already exist.
- Run the handler locally against supported development sources.
- Validate linked repository paths and required local configuration before runtime execution.
- Print clear next steps after generation or infrastructure actions.

## Contracts

- Binary name: `triage`
- Command surface:
  - `triage init`
  - `triage infra generate`
  - `triage infra plan`
  - `triage infra apply`
  - `triage run`
- Credential model:
  - GCP uses local Application Default Credentials
  - AWS uses local CLI credentials, profiles, or environment variables
  - the CLI does not implement login flows
- Expected generated artifacts:
  - `triage.yaml`
  - cloud-specific Terraform inputs
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
- Generated outputs must be deterministic and idempotent from the same inputs.
- The CLI keeps both generation and local-run responsibilities in scope for the MVP documentation.

## Open questions

- See [OQ-108](../90-open-questions.md#oq-108) for whether Terraform execution remains a first-class CLI responsibility or a convenience wrapper.

## Deferred items

- Richer interactive UX and guided setup
- Additional scaffolds beyond the initial OpenIncidents layout
- Non-Terraform deployment backends
