# Spec and Governance Reorganization

Date: 2026-03-08

## Related specs

- [Triage Specification Index](../../SPECS/triage/README.md)
- [OpenIncidents Product Overview](../../SPECS/triage/00-product-overview.md)
- [OpenIncidents System Architecture](../../SPECS/triage/01-system-architecture.md)
- [OpenIncidents Open Questions](../../SPECS/triage/90-open-questions.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth for repo behavior and documentation workflow.
- The repo is documentation-first until specs are sufficiently closed.
- `.codex` notes must not override policy, scope, naming, or workflow defined in `AGENTS.md`.

## Decisions

- Reorganized the canonical spec set under `SPECS/triage/`.
- Locked the canonical names `OpenIncidents`, `triage`, and `triage-handler`.
- Established `90-open-questions.md` as the only canonical backlog for unresolved design decisions.
- Created `.codex/topics/` as the working layer for one note per chat or work topic.

## Open questions

- The open-question set must be tracked only in the canonical specs; consult `SPECS/triage/90-open-questions.md` for the current unresolved items.

## Next documentation changes

- Refine open questions as product decisions are made.
- Tighten subsystem docs once implementation order is chosen.
- Keep future topic notes linked to the relevant canonical specs.

## Session updates (MVP requirements alignment)

- Updated canonical specs to align the MVP with error-first log triage, linked repository analysis, optional LLM diagnostics, and Slack or Discord reporting with optional Jira escalation.
- Kept `triage-handler` as a shared runtime contract while documenting official Go and Python handler templates.
- Added explicit `.env` development posture in specs and preserved the rule that secrets must not live directly in canonical config files.

## Session updates (decision closure)

- Closed the former uncertainty around GCP Pub/Sub push delivery on Cloud Run.
- Closed the former uncertainty around AWS zip packaging for the documented MVP path.
- Closed the former uncertainty around CLI ownership of Terraform `plan/apply` by keeping them in the official `triage` workflow.
