# Triage Bootstrap and Planning Freeze

## Related specs

- [../../SPECS/triage/10-runtime/10-cli.md](../../SPECS/triage/10-runtime/10-cli.md)
- [../../SPECS/triage/10-runtime/12-cli-state.md](../../SPECS/triage/10-runtime/12-cli-state.md)
- [../../SPECS/triage/30-integrations/30-config.md](../../SPECS/triage/30-integrations/30-config.md)
- [../../SPECS/triage/30-integrations/31-llm.md](../../SPECS/triage/30-integrations/31-llm.md)
- [../../SPECS/triage/40-governance/40-security-iam.md](../../SPECS/triage/40-governance/40-security-iam.md)

## AGENTS constraints used

- OpenIncidents is in a documentation-first phase.
- `SPECS/triage/` remains the canonical planning surface.
- `triage` is the canonical CLI name.
- Do not write product code while the planning freeze remains active.
- Commit and push are allowed during the freeze only for Markdown-only change sets.

## Decisions captured

- `triage init` is the required bootstrap step before operational CLI commands.
- Bootstrap validates real local cloud credentials and required binaries.
- `triage` stores per-user bootstrap state in a cross-platform JSON file outside the repository.
- The raw LLM token is stored only in the local CLI state file during the current planning phase.
- The planning freeze blocks product code and any non-Markdown commit or push until the user explicitly lifts it.

## Open questions still relevant

- [OQ-105](../../SPECS/triage/90-open-questions.md#oq-105)
- [OQ-107](../../SPECS/triage/90-open-questions.md#oq-107)

## Follow-up

- Keep future CLI documentation aligned with the bootstrap gating model.
- Revisit local token persistence once keychain or secret-store integration is ready to be specified.
