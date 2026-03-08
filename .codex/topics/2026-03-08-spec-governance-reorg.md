# Spec and Governance Reorganization

Date: 2026-03-08

## Related specs

- [OpenIncidents Specification Index](../../SPECS/chrisloarryn/README.md)
- [OpenIncidents Product Overview](../../SPECS/chrisloarryn/00-product-overview.md)
- [OpenIncidents System Architecture](../../SPECS/chrisloarryn/01-system-architecture.md)
- [OpenIncidents Open Questions](../../SPECS/chrisloarryn/90-open-questions.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth for repo behavior and documentation workflow.
- The repo is documentation-first until specs are sufficiently closed.
- `.codex` notes must not override policy, scope, naming, or workflow defined in `AGENTS.md`.

## Decisions

- Reorganized `SPECS/chrisloarryn/` into root guidance plus subsystem subfolders.
- Locked the canonical names `OpenIncidents`, `triage`, and `triage-handler`.
- Established `90-open-questions.md` as the only canonical backlog for unresolved design decisions.
- Created `.codex/topics/` as the working layer for one note per chat or work topic.

## Open questions

- OQ-101 through OQ-108 remain unresolved and must be settled in the canonical specs, not only in this note.

## Next documentation changes

- Refine open questions as product decisions are made.
- Tighten subsystem docs once implementation order is chosen.
- Keep future topic notes linked to the relevant canonical specs.
