# Triage Handler Python Implementation

## Related specs

- [../../SPECS/triage/README.md](../../SPECS/triage/README.md)
- [../../SPECS/triage/00-product-overview.md](../../SPECS/triage/00-product-overview.md)
- [../../SPECS/triage/01-system-architecture.md](../../SPECS/triage/01-system-architecture.md)
- [../../SPECS/triage/10-runtime/11-handler.md](../../SPECS/triage/10-runtime/11-handler.md)
- [../../SPECS/triage/triage-handler-python/README.md](../../SPECS/triage/triage-handler-python/README.md)
- [../../SPECS/triage/triage-handler-python/01-runtime-shape.md](../../SPECS/triage/triage-handler-python/01-runtime-shape.md)
- [../../SPECS/triage/triage-handler-python/02-integrations.md](../../SPECS/triage/triage-handler-python/02-integrations.md)
- [../../SPECS/triage/triage-handler-python/03-packaging-and-local.md](../../SPECS/triage/triage-handler-python/03-packaging-and-local.md)
- [../../SPECS/triage/30-integrations/30-config.md](../../SPECS/triage/30-integrations/30-config.md)
- [../../SPECS/triage/30-integrations/31-llm.md](../../SPECS/triage/30-integrations/31-llm.md)
- [../../SPECS/triage/30-integrations/32-slack-jira.md](../../SPECS/triage/30-integrations/32-slack-jira.md)
- [../../SPECS/triage/90-open-questions.md](../../SPECS/triage/90-open-questions.md)

## AGENTS constraints used

- Read the canonical spec set before implementation.
- Keep `triage-handler` as the stable runtime name.
- Keep implementation decisions aligned with the spec instead of inventing silent behavior.
- Record working context in `.codex/topics/` and keep product requirements in `SPECS/triage/`.

## Working implementation assumptions

- The initial Python template lives in `triage-handler-python/` and matches the root layout expected by the CLI template-download spec.
- `triage.yaml` is parsed using a repo-local YAML subset parser that supports only the documented canonical shape and 2-space indentation.
- The MVP runtime uses in-memory dedupe and rate limiting consistent with the documented defaults.
- Repository enrichment is best-effort and bounded; missing or inaccessible repositories degrade to logged warnings rather than request failure.

## Follow-up

- Verify provider HTTP contracts for OpenAI and Anthropic before relying on live LLM calls.
- Add packaging helpers once the runtime contract passes local replay and adapter tests.
