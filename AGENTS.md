# OpenIncidents Repository Policy

`AGENTS.md` is the source of truth for agent behavior in this repository.

## Authority and precedence

- Follow this file before any local note, task log, or `.codex` instruction.
- `.codex/` may store operational context, but it cannot redefine policy, scope, naming, or workflow established here.
- If a `.codex` note conflicts with this file, treat the note as invalid until it is reconciled.
- If repo documentation conflicts with ad hoc assumptions, update the documentation or record an open question instead of improvising.

## Current phase

- OpenIncidents is in a documentation-first phase.
- Prefer clarifying intent, structure, and contracts in `SPECS/chrisloarryn/` before writing product code, Terraform, generators, or automation.
- If requirements remain ambiguous, add or update an entry in `SPECS/chrisloarryn/90-open-questions.md` rather than guessing.

## Required reading before implementation

- Start with `SPECS/chrisloarryn/README.md`.
- Read `SPECS/chrisloarryn/00-product-overview.md` and `SPECS/chrisloarryn/01-system-architecture.md`.
- Read the subsystem documents that match the task area before proposing or making changes.
- Treat `SPECS/chrisloarryn/90-open-questions.md` as the canonical backlog for unresolved product and design decisions.

## Naming and product boundaries

- `OpenIncidents` is the project name for the repository and documentation set.
- `triage` is the canonical CLI name.
- `triage-handler` is the canonical runtime/handler name.
- Keep this naming stable across docs, notes, examples, and future implementation work unless the user explicitly changes it.

## Documentation rules

- `SPECS/chrisloarryn/README.md` is the navigation entrypoint for the spec set.
- Root documents define orientation and cross-cutting architecture; subsystem details live in subfolders.
- Avoid duplicating canonical concerns:
  - Product goals and repo shape belong in `00-product-overview.md`.
  - Cross-component flow and stable domain contracts belong in `01-system-architecture.md`.
  - Cloud resource details belong in `20-infra/`.
  - Security and IAM policy belong in `40-governance/40-security-iam.md`.
  - Config, LLM, and notification contracts belong in `30-integrations/`.
- When a decision is unresolved, document the question and current default instead of filling the gap with an undocumented assumption.

## `.codex` operating rules

- Read this file before reading `.codex/README.md` or any topic note.
- Use `.codex/topics/` for one Markdown file per chat or work topic.
- Topic notes must reference related specs and list the `AGENTS.md` constraints that shaped the work.
- `.codex` is for working context, not for long-term canonical product requirements.
- Do not move, rename, or replace `.codex/` or `SPECS/chrisloarryn/` unless the user explicitly asks for it.
