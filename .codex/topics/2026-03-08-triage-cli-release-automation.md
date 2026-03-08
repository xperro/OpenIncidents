# Triage CLI Release Automation

Date: 2026-03-08

## Related specs

- [../../SPECS/triage/10-runtime/10-cli.md](../../SPECS/triage/10-runtime/10-cli.md)
- [../../SPECS/triage/10-runtime/13-cli-release.md](../../SPECS/triage/10-runtime/13-cli-release.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth.
- The thread stays focused on CLI work only.
- Canonical contracts must be documented in `SPECS/triage/` before implementation.

## Decisions

- GitHub Actions is the canonical CI and release automation path for the Python CLI.
- The release bundle is built as `triage.pyz` plus thin Unix and Windows launchers.
- GitHub Releases are the publication surface for the CLI in the current phase.

## Open questions

- None currently captured beyond the canonical specs.

## Next documentation changes

- Keep release asset names and smoke checks synchronized with `.github/workflows/`.
