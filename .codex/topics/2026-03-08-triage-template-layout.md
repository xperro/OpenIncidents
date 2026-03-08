# 2026-03-08 - triage template physical layout

## Context

- Work topic: migrate handler templates to the physical `templates/<runtime>/<cloud>` layout
- Canonical policy source: [../../AGENTS.md](../../AGENTS.md)
- Canonical specs:
  - [../../SPECS/triage/10-runtime/10-cli.md](../../SPECS/triage/10-runtime/10-cli.md)
  - [../../SPECS/triage/10-runtime/11-handler.md](../../SPECS/triage/10-runtime/11-handler.md)
  - [../../SPECS/triage/triage-handler-go/README.md](../../SPECS/triage/triage-handler-go/README.md)
  - [../../SPECS/triage/triage-handler-python/README.md](../../SPECS/triage/triage-handler-python/README.md)

## AGENTS.md constraints applied

- Kept `triage` as the CLI name and `triage-handler` as the runtime name.
- Updated canonical specs together with implementation instead of improvising a hidden layout.
- Worked with the existing untracked CLI/test trees instead of discarding them.

## Implemented scope

- Added `templates/go/gcp`, `templates/go/aws`, `templates/python/gcp`, and `templates/python/aws`
- Switched CLI template download from generated placeholders to recursive copy from the physical template tree
- Added variant-specific `handler-path` validation for `run` and `infra apply`
- Normalized Go local replay entrypoint to `cmd/triage-handler-local`
- Added CLI tests for:
  - physical template copy
  - `--force`
  - relative path rejection
  - junk file filtering
  - Go local replay
  - wrong-variant rejection in packaging

## Notes

- The physical templates are minimal runnable variants, not yet the full production handler implementation described in the higher-level specs.
- Python GCP includes a Starlette app entrypoint, while Python AWS keeps a Lambda-style entrypoint and stdlib local replay.
