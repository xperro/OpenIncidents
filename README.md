# OpenIncidents

OpenIncidents is in a documentation-first phase. The canonical source of truth for product and technical direction lives in [AGENTS.md](AGENTS.md) and in [SPECS/incidenWatcher/README.md](SPECS/incidenWatcher/README.md).

## Current documented product shape

- `triage` is the CLI.
- `triage-handler` is the runtime contract.
- GCP and AWS are official deployment targets.
- Go and Python are the official handler template runtimes.
- Slack and Discord are primary notification channels, with optional Jira escalation.
- OpenAI and Anthropic are the named optional LLM providers.

## Read order

1. [AGENTS.md](AGENTS.md)
2. [SPECS/incidenWatcher/README.md](SPECS/incidenWatcher/README.md)
3. [SPECS/incidenWatcher/00-product-overview.md](SPECS/incidenWatcher/00-product-overview.md)
4. [SPECS/incidenWatcher/01-system-architecture.md](SPECS/incidenWatcher/01-system-architecture.md)
5. subsystem specs under [SPECS/incidenWatcher](SPECS/incidenWatcher)

This root README is orientation only. It should not be used as a substitute for the canonical specs.
