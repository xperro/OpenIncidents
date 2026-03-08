# Comparative Summary: `chrisloarryn` vs `xperro`

## High-level comparison

`SPECS/chrisloarryn/` is a structured spec set for OpenIncidents. `SPECS/xperro/` is still a minimal placeholder with no substantive design content yet.

## Side-by-side view

| Area | `SPECS/chrisloarryn/` | `SPECS/xperro/` |
| --- | --- | --- |
| Purpose | Defines product, architecture, runtime, infra, integrations, and governance for OpenIncidents | No defined purpose yet beyond a placeholder file |
| Structure | Multi-document spec tree with layered organization | Single text file |
| Maturity | High for planning/documentation | Very early / placeholder |
| Naming | Canonical names are documented and stable | No naming contract |
| Scope boundaries | Explicit MVP, non-goals, deferred items, open questions | None |
| Runtime model | Defined CLI and handler roles | None |
| Infra model | GCP and AWS contracts documented | None |
| Integrations | Config, LLM, Slack, Jira documented | None |
| Governance | Security and IAM documented | None |
| Decision tracking | Open question backlog with defaults | None |

## Practical interpretation

- `chrisloarryn` can already guide future implementation work.
- `xperro` cannot yet guide implementation because it has no real requirements or contracts.
- If both directories are meant to represent ideas at similar maturity, `xperro` needs a substantial documentation pass to become comparable.

## Recommended next step

Either:

1. grow `SPECS/xperro/` into a real spec set with at least goals, scope, architecture, and open questions, or
2. keep it explicitly marked as an experimental placeholder so it is not mistaken for a usable source of truth
