# OpenIncidents

OpenIncidents esta en una fase documentation-first. La fuente de verdad para direccion de producto y tecnica vive en [AGENTS.md](AGENTS.md) y en [SPECS/chrisloarryn/README.md](SPECS/chrisloarryn/README.md).

## Forma actual del producto documentado

- `triage` es el CLI.
- `triage-handler` es el contrato del runtime.
- GCP y AWS son targets oficiales de despliegue.
- Go y Python son los runtimes oficiales de template para el handler.
- Slack y Discord son los canales primarios de notificacion, con escalamiento opcional a Jira.
- OpenAI y Anthropic son los proveedores LLM opcionales nombrados.

## Orden de lectura

1. [AGENTS.md](AGENTS.md)
2. [SPECS/chrisloarryn/README.md](SPECS/chrisloarryn/README.md)
3. [SPECS/chrisloarryn/00-product-overview.md](SPECS/chrisloarryn/00-product-overview.md)
4. [SPECS/chrisloarryn/01-system-architecture.md](SPECS/chrisloarryn/01-system-architecture.md)
5. los subsistemas bajo [SPECS/chrisloarryn](SPECS/chrisloarryn)

Este LEEME es solo orientacion y no reemplaza las specs canonicas.
