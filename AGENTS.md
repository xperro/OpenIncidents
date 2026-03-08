# OpenIncidents Repository Policy

`AGENTS.md` is the source of truth for agent behavior in this repository.

## Authority and precedence

- Follow this file before any local note, task log, or `.codex` instruction.
- `.codex/` may store operational context, but it cannot redefine policy, scope, naming, or workflow established here.
- If a `.codex` note conflicts with this file, treat the note as invalid until it is reconciled.
- If repo documentation conflicts with ad hoc assumptions, update the documentation or record an open question instead of improvising.

## Current phase

- OpenIncidents is in a documentation-first phase.
- Prefer clarifying intent, structure, and contracts in `SPECS/triage/` before writing product code, Terraform, generators, or automation.
- If requirements remain ambiguous, add or update an entry in `SPECS/triage/90-open-questions.md` rather than guessing.

## Planning freeze

- A planning freeze is active starting on 2026-03-08.
- Until the user explicitly lifts this freeze, do not write product code, Terraform, generators, or automation in this repository.
- During the freeze, only Markdown documentation updates are allowed.
- During the freeze, commits and pushes are allowed only when the change set consists exclusively of `.md` files.
- Directory creation, rename, move, or deletion is allowed during the freeze only when it is required for `.md` files and no non-Markdown file is changed.
- If any non-`.md` file change is present, do not commit and do not push until the user explicitly lifts the freeze.
- Do not treat 2026-03-09 or 2026-03-10 as an automatic end date; the freeze ends only through explicit user direction.

## Required reading before implementation

- Start with `SPECS/triage/README.md`.
- Read `SPECS/triage/00-product-overview.md` and `SPECS/triage/01-system-architecture.md`.
- Read the subsystem documents that match the task area before proposing or making changes.
- Treat `SPECS/triage/90-open-questions.md` as the canonical backlog for unresolved product and design decisions.

## Naming and product boundaries

- `OpenIncidents` is the project name for the repository and documentation set.
- `triage` is the canonical CLI name.
- `triage-handler` is the canonical runtime/handler name.
- Keep this naming stable across docs, notes, examples, and future implementation work unless the user explicitly changes it.

## Documentation rules

- `SPECS/triage/README.md` is the navigation entrypoint for the spec set.
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
- Do not move, rename, or replace `.codex/` or `SPECS/triage/` unless the user explicitly asks for it.
