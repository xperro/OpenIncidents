# OpenIncidents Specification Index

This directory is the canonical planning workspace for OpenIncidents.

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
5. [90-open-questions.md](90-open-questions.md) for unresolved decisions and current defaults

## Layout

- [00-product-overview.md](00-product-overview.md): product framing, MVP boundaries, and naming contract
- [01-system-architecture.md](01-system-architecture.md): cross-component flow and stable domain contracts
- [10-runtime/10-cli.md](10-runtime/10-cli.md): CLI responsibilities and command surface
- [10-runtime/11-handler.md](10-runtime/11-handler.md): runtime pipeline and handler behavior
- [20-infra/20-gcp-terraform.md](20-infra/20-gcp-terraform.md): GCP deployment contract
- [20-infra/21-aws-terraform.md](20-infra/21-aws-terraform.md): AWS deployment contract
- [30-integrations/30-config.md](30-integrations/30-config.md): `triage.yaml` schema and precedence
- [30-integrations/31-llm.md](30-integrations/31-llm.md): optional LLM integration contract
- [30-integrations/32-slack-jira.md](30-integrations/32-slack-jira.md): Slack and Jira notification contracts
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
