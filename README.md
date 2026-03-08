
# Monitor Agent MVP

AI-assisted incident analysis agent for microservices.

The Monitor Agent reads recent logs from cloud providers (GCP or AWS), detects relevant errors,
correlates them with source code in local repositories, generates hypotheses using an LLM,
and posts a preliminary incident report to Slack.

This project is designed as an MVP executed locally before being automated in cloud infrastructure.

---

## Goal

Accelerate the initial diagnosis of incidents by combining:

- Cloud logs
- Source code context
- AI analysis
- Automated Slack reporting

---

## MVP Scope

Includes:

- Manual CLI execution
- Configurable log window (ex: last 10 minutes)
- GCP Cloud Logging or AWS CloudWatch support
- Error grouping
- Source code context search
- LLM-based analysis
- Slack reporting

Not included:

- Cron automation
- Infrastructure deployment
- Auto-remediation
- Ticket creation
- Historical memory

---

## Project Structure

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
```

---

## Example Execution

python -m monitor_agent.main run --service payments-orchestrator
