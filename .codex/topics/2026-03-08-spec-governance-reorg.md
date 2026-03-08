# Spec and Governance Reorganization

Date: 2026-03-08

## Related specs

- [OpenIncidents Specification Index](../../SPECS/incidenWatcher/README.md)
- [OpenIncidents Product Overview](../../SPECS/incidenWatcher/00-product-overview.md)
- [OpenIncidents System Architecture](../../SPECS/incidenWatcher/01-system-architecture.md)
- [OpenIncidents Open Questions](../../SPECS/incidenWatcher/90-open-questions.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth for repo behavior and documentation workflow.
- The repo is documentation-first until specs are sufficiently closed.
- `.codex` notes must not override policy, scope, naming, or workflow defined in `AGENTS.md`.

## Decisions

- Reorganized `SPECS/incidenWatcher/` into root guidance plus subsystem subfolders.
- Locked the canonical names `OpenIncidents`, `triage`, and `triage-handler`.
- Established `90-open-questions.md` as the only canonical backlog for unresolved design decisions.
- Created `.codex/topics/` as the working layer for one note per chat or work topic.

## Open questions

- The open-question set must be tracked only in the canonical specs; consult `SPECS/chrisloarryn/90-open-questions.md` for the current unresolved items.

## Next documentation changes

- Refine open questions as product decisions are made.
- Tighten subsystem docs once implementation order is chosen.
- Keep future topic notes linked to the relevant canonical specs.

## Session updates (MVP requirements alignment)

- Updated canonical specs to align MVP with error-first log triage, linked repository analysis, optional LLM diagnostics, and Slack or Discord reporting.
- Updated runtime direction to Python while keeping canonical names `OpenIncidents`, `triage`, and `triage-handler`.
- Added explicit `.env` development posture in specs and created `.gitignore`/`.env.example` to prevent secret commits.
- Added OQ-109 and OQ-110 in the canonical backlog for notifier precedence and repository access model decisions.

## Session updates (decision closure)

- Closed first-cloud sequencing as GCP-first while keeping AWS configurable in the MVP contract.
- Closed notifier direction to configurable Slack/Discord routing (`slack`, `discord`, `both`) and deferred Jira to post-MVP.
- Closed repository access direction to Git URL + credentials (env-referenced), with optional local cache path for efficient context extraction.
