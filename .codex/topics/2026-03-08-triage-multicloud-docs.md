# Triage Multi-Cloud Docs Update

Date: 2026-03-08

## Related specs

- [Triage Specification Index](../../SPECS/triage/README.md)
- [OpenIncidents Product Overview](../../SPECS/triage/00-product-overview.md)
- [OpenIncidents System Architecture](../../SPECS/triage/01-system-architecture.md)
- [CLI Specification: triage](../../SPECS/triage/10-runtime/10-cli.md)
- [Runtime Specification: triage-handler](../../SPECS/triage/10-runtime/11-handler.md)
- [OpenIncidents Open Questions](../../SPECS/triage/90-open-questions.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth for repo behavior and documentation workflow.
- The repo remains documentation-first until specs are sufficiently closed.
- Canonical naming stays `OpenIncidents`, `triage`, and `triage-handler`.
- `.codex` notes cannot override canonical specs.

## Decisions

- Documented `triage` as the official multi-cloud CLI for GCP and AWS.
- Added official handler template support in Go and Python.
- Elevated Discord to a named MVP integration alongside Slack and Jira.
- Locked absolute-path requirements for template output and handler deployment paths.
- Closed prior doc-level uncertainty around GCP push delivery, AWS zip packaging, and CLI ownership of Terraform plan/apply.

## Open questions

- OQ-104 still covers dedupe and rate-limit state placement.
- OQ-105 still covers the mandatory LLM redaction baseline.
- OQ-106 still covers the Jira escalation threshold.
- OQ-107 still covers when cloud secret stores become mandatory.

## Next documentation changes

- Keep implementation work aligned with the new CLI and config contracts.
- Add examples once the first code implementation exists.
- Revisit notifier payload details only if Slack, Discord, or Jira behavior diverges from the shared contract.
