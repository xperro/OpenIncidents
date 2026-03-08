# OpenIncidents

OpenIncidents esta en una fase documentation-first. La fuente de verdad para direccion de producto y tecnica vive en [AGENTS.md](AGENTS.md) y en [SPECS/triage/README.md](SPECS/triage/README.md).

## Forma actual del producto documentado

- `triage` es el CLI.
- `triage-handler` es el contrato del runtime.
- GCP y AWS son targets oficiales de despliegue.
- Go y Python son los runtimes oficiales de template para el handler.
- Los templates fisicos del handler viven en `triage/templates/go/gcp`, `triage/templates/go/aws`, `triage/templates/python/gcp` y `triage/templates/python/aws`.
- Slack y Discord son los canales primarios de notificacion, con escalamiento opcional a Jira.
- OpenAI y Anthropic son los proveedores LLM opcionales nombrados.

## Orden de lectura

1. [AGENTS.md](AGENTS.md)
2. [SPECS/triage/README.md](SPECS/triage/README.md)
3. [SPECS/triage/00-product-overview.md](SPECS/triage/00-product-overview.md)
4. [SPECS/triage/01-system-architecture.md](SPECS/triage/01-system-architecture.md)
5. los subsistemas bajo [SPECS/triage](SPECS/triage)

Este LEEME es solo orientacion y no reemplaza las specs canonicas.
