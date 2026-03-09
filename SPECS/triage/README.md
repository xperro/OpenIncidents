# Triage Specification Index

This directory is the canonical planning workspace for the `triage` specification set in OpenIncidents.

## Naming

- `OpenIncidents` is the project name.
- `triage` is the CLI name.
- `triage-handler` is the runtime name.
- `AGENTS.md` remains the repo policy; these specs define product and technical intent.

## Read order

1. [README.md](README.md)
2. [00-product-overview.md](00-product-overview.md)
3. [01-system-architecture.md](01-system-architecture.md)
4. Subsystem documents in `10-runtime/`, `20-infra/`, `30-integrations/`, and `40-governance/`
5. Language-specific handler detail in [triage-handler-go/README.md](triage-handler-go/README.md) and [triage-handler-python/README.md](triage-handler-python/README.md)
6. [90-open-questions.md](90-open-questions.md) for unresolved decisions and current defaults

## Layout

- [00-product-overview.md](00-product-overview.md): product framing, MVP boundaries, naming, and platform expectations
- [01-system-architecture.md](01-system-architecture.md): cross-component flow and stable domain contracts
- [10-runtime/10-cli.md](10-runtime/10-cli.md): CLI responsibilities, template handling, and deployment workflow
- [10-runtime/11-handler.md](10-runtime/11-handler.md): shared serverless receiver service contract and runtime behavior across official templates
- [10-runtime/12-cli-state.md](10-runtime/12-cli-state.md): per-user local bootstrap state and persistent CLI settings
- [10-runtime/13-cli-release.md](10-runtime/13-cli-release.md): GitHub Actions CI, release packaging, and published CLI assets
- [triage-handler-go/README.md](triage-handler-go/README.md): Go-specific receiver service implementation detail for `triage-handler`
- [triage-handler-python/README.md](triage-handler-python/README.md): Python-specific receiver service implementation detail for `triage-handler`
- [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md): GCP deployment contract
- [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md): AWS deployment contract
- [30-integrations/30-config.md](30-integrations/30-config.md): `triage.yaml` schema and precedence
- [30-integrations/31-llm.md](30-integrations/31-llm.md): optional LLM integration contract
- [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md): Slack, Discord, and Jira notification contracts
- [30-integrations/33-config-operations.md](30-integrations/33-config-operations.md): operator workflow for finding and changing configuration
- [30-integrations/34-llm-prep-workflow.md](30-integrations/34-llm-prep-workflow.md): isolated `llm-prep -> llm-request -> llm-client` workflow and payload examples
- [40-governance/40-security-iam.md](40-governance/40-security-iam.md): canonical security and IAM policy
- [90-open-questions.md](90-open-questions.md): open decision backlog

## Working rules

- Each spec document follows the same internal template:
  - `Intent`
  - `Scope`
  - `Responsibilities`
  - `Contracts`
  - `Dependencies`
  - `Locked decisions`
  - `Open questions`
  - `Deferred items`
- Keep one canonical home for each concern and link outward instead of duplicating content.
- Record unresolved decisions in [90-open-questions.md](90-open-questions.md) instead of leaving silent gaps.
- Keep `.codex/` aligned with [../../AGENTS.md](../../AGENTS.md); `.codex` notes are never normative.
