# Triage Config Discoverability

## Related specs

- [../../SPECS/triage/10-runtime/10-cli.md](../../SPECS/triage/10-runtime/10-cli.md)
- [../../SPECS/triage/10-runtime/12-cli-state.md](../../SPECS/triage/10-runtime/12-cli-state.md)
- [../../SPECS/triage/30-integrations/30-config.md](../../SPECS/triage/30-integrations/30-config.md)
- [../../SPECS/triage/30-integrations/32-slack-jira.md](../../SPECS/triage/30-integrations/32-slack-jira.md)
- [../../SPECS/triage/30-integrations/33-config-operations.md](../../SPECS/triage/30-integrations/33-config-operations.md)

## AGENTS constraints used

- OpenIncidents remains documentation-first until implementation work begins.
- `SPECS/triage/` is the canonical planning surface.
- `triage` is the canonical CLI name.
- Configuration contracts should be clarified in specs instead of left to implementation assumptions.

## Decisions captured

- `triage config` is the recommended operator-facing surface for finding and changing configuration.
- `triage settings` remains the low-level local-state surface.
- The per-user CLI home is `~/.triage/` on Linux and macOS and `%APPDATA%/triage/` on Windows.
- The project `.triage/` directory remains separate from the per-user CLI home.
- The config wizard may rewrite `triage.yaml` only within the documented canonical YAML subset.

## Follow-up

- Keep future CLI examples aligned with `triage config show`, `triage config where`, and `triage config wizard`.
- Keep Jira-related operator docs pointing back to the config operations guide instead of duplicating change instructions.
