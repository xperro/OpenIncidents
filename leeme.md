
# Monitor Agent MVP

Agente de análisis de incidentes para microservicios asistido por IA.

El Monitor Agent lee logs recientes desde proveedores cloud (GCP o AWS),
detecta errores relevantes, los relaciona con el código fuente del repositorio,
genera hipótesis mediante un modelo LLM y publica un reporte preliminar en Slack.

Este proyecto está diseñado como MVP ejecutado localmente antes de automatizar
su despliegue en infraestructura cloud.

---

## Objetivo

Acelerar el diagnóstico inicial de incidentes combinando:

- logs cloud
- contexto del código fuente
- análisis con IA
- reporte automático en Slack

---

## Alcance del MVP

Incluye:

- ejecución manual por CLI
- ventana configurable de logs
- soporte para GCP o AWS
- agrupación de errores
- búsqueda de contexto en repositorios
- análisis con LLM
- reporte en Slack

No incluye:

- cron o scheduler
- despliegue cloud
- auto-remediación
- creación de tickets
- memoria histórica

---

## Estructura del Proyecto

```text
monitor-agent/
├─ README.md
├─ LEEME.md
├─ pyproject.toml
├─ config/
│  └─ settings.yaml
├─ src/
│  └─ monitor_agent/
│     ├─ main.py
│     ├─ cli/
│     ├─ core/
│     ├─ providers/
│     ├─ services/
│     ├─ domain/
│     └─ utils/
└─ tests/

---

## Ejecución

python -m monitor_agent.main run --service payments-orchestrator
