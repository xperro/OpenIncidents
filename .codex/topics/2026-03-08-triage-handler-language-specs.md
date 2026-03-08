# Triage Handler Language Specs

Date: 2026-03-08

## Related specs

- [Triage Specification Index](../../SPECS/triage/README.md)
- [OpenIncidents Product Overview](../../SPECS/triage/00-product-overview.md)
- [CLI Specification: triage](../../SPECS/triage/10-runtime/10-cli.md)
- [Runtime Specification: triage-handler](../../SPECS/triage/10-runtime/11-handler.md)

## AGENTS constraints

- `AGENTS.md` is the source of truth for repo behavior and documentation workflow.
- The repo remains documentation-first until specs are sufficiently closed.
- Canonical naming stays `OpenIncidents`, `triage`, and `triage-handler`.
- `.codex` notes cannot override canonical specs.

## Decisions

- Added `SPECS/triage/triage-handler-go/` and `SPECS/triage/triage-handler-python/` as language-specific handler spec areas.
- Kept `SPECS/triage/10-runtime/11-handler.md` as the shared runtime contract.
- Fixed the official `triage` CLI implementation target to Python using only the standard library.
- Kept Go and Python as the official handler/runtime paths, with Python handler helper entrypoints and HTTP/JSON integrations staying in the standard library.

## Open questions

- OQ-104 still covers dedupe and rate-limit state placement.
- OQ-106 still covers Jira escalation thresholds.
- OQ-107 still covers secret-store hardening thresholds.

## Next documentation changes

- Add implementation examples only after code work begins.
- Keep language-specific docs aligned if the shared runtime contract changes.
