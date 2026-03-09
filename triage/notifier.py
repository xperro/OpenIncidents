"""Notifier module for llm-analysis outputs."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from .errors import UserError


VALID_TARGETS = ("slack", "discord", "jira")
SEVERITY_ORDER = {
    "EMERGENCY": 8,
    "ALERT": 7,
    "CRITICAL": 6,
    "ERROR": 5,
    "WARNING": 4,
    "NOTICE": 3,
    "INFO": 2,
    "DEBUG": 1,
    "UNKNOWN": 0,
}
SEVERITY_COLOR = {
    "EMERGENCY": 0x8B0000,
    "ALERT": 0xB22222,
    "CRITICAL": 0xDC143C,
    "ERROR": 0xE74C3C,
    "WARNING": 0xF39C12,
    "NOTICE": 0xF1C40F,
    "INFO": 0x3498DB,
    "DEBUG": 0x95A5A6,
    "UNKNOWN": 0x7F8C8D,
}


def notify_analysis(
    analysis_payload: dict[str, Any],
    *,
    targets: list[str],
    env: dict[str, str],
    project: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    language = resolve_language(env, analysis_payload)
    results = []
    for target in targets:
        if target not in VALID_TARGETS:
            raise UserError(f"Unsupported notifier target: {target}")
        if target == "slack":
            results.extend(send_slack(analysis_payload, env=env, dry_run=dry_run, language=language))
        elif target == "discord":
            results.extend(send_discord(analysis_payload, env=env, dry_run=dry_run, language=language))
        else:
            results.extend(send_jira(analysis_payload, env=env, project=project or {}, dry_run=dry_run, language=language))
    sent = sum(1 for item in results if item.get("status") == "sent")
    simulated = sum(1 for item in results if item.get("status") == "simulated")
    skipped = sum(1 for item in results if item.get("status", "").startswith("skipped"))
    return {
        "schema_version": "llm-notify.v1",
        "targets": targets,
        "language": language,
        "dry_run": dry_run,
        "results": results,
        "meta": {
            "attempted": len(results),
            "sent": sent,
            "simulated": simulated,
            "skipped": skipped,
        },
    }


def send_slack(
    analysis_payload: dict[str, Any],
    *,
    env: dict[str, str],
    dry_run: bool,
    language: str,
) -> list[dict[str, Any]]:
    webhook = str(env.get("SLACK_WEBHOOK_URL", "")).strip()
    if not webhook:
        return [{"target": "slack", "status": "skipped_missing_config", "reason": "SLACK_WEBHOOK_URL not set"}]
    results = []
    for result in iter_results(analysis_payload):
        payload = {
            "text": format_message_line(result, language=language),
        }
        results.append(send_webhook("slack", webhook, payload, dry_run=dry_run))
    return results


def send_discord(
    analysis_payload: dict[str, Any],
    *,
    env: dict[str, str],
    dry_run: bool,
    language: str,
) -> list[dict[str, Any]]:
    webhook = str(env.get("DISCORD_WEBHOOK_URL", "")).strip()
    if not webhook:
        return [{"target": "discord", "status": "skipped_missing_config", "reason": "DISCORD_WEBHOOK_URL not set"}]
    results = []
    for result in iter_results(analysis_payload):
        payload = build_discord_payload(result, language=language)
        results.append(send_webhook("discord", webhook, payload, dry_run=dry_run))
    return results


def send_jira(
    analysis_payload: dict[str, Any],
    *,
    env: dict[str, str],
    project: dict[str, Any],
    dry_run: bool,
    language: str,
) -> list[dict[str, Any]]:
    jira_cfg = (project.get("integrations") or {}).get("jira") if isinstance(project, dict) else {}
    base_url = str(env.get("JIRA_BASE_URL", "")).strip() or str((jira_cfg or {}).get("base_url") or "").strip()
    project_key = str(env.get("JIRA_PROJECT_KEY", "")).strip() or str((jira_cfg or {}).get("project_key") or "").strip()
    issue_type = str(env.get("JIRA_ISSUE_TYPE", "")).strip() or str((jira_cfg or {}).get("issue_type") or "Bug").strip()
    email = str(env.get("JIRA_EMAIL", "")).strip()
    token = str(env.get("JIRA_API_TOKEN", "")).strip()
    if not base_url or not project_key or not email or not token:
        return [
            {
                "target": "jira",
                "status": "skipped_missing_config",
                "reason": "JIRA_BASE_URL/JIRA_PROJECT_KEY/JIRA_EMAIL/JIRA_API_TOKEN incomplete",
            }
        ]

    results = []
    endpoint = base_url.rstrip("/") + "/rest/api/3/issue"
    auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    for result in iter_results(analysis_payload):
        summary = result["analysis"].get("summary") or f"Incident {result['incident_id']}"
        description = build_jira_description(result, language=language)
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[OpenIncidents] {summary}"[:255],
                "description": description,
                "issuetype": {"name": issue_type},
            }
        }
        headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
        results.append(send_http_json("jira", endpoint, payload, headers=headers, dry_run=dry_run))
    return results


def iter_results(analysis_payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = analysis_payload.get("results")
    if not isinstance(results, list):
        return []
    filtered = []
    for item in results:
        if not isinstance(item, dict):
            continue
        analysis = item.get("analysis")
        if not isinstance(analysis, dict):
            continue
        filtered.append(item)
    filtered.sort(
        key=lambda item: severity_weight(resolve_severity(item)),
        reverse=True,
    )
    return filtered


def format_message_line(result: dict[str, Any], *, language: str) -> str:
    analysis = result.get("analysis") or {}
    summary = str(analysis.get("summary") or "No summary")
    cause = str(analysis.get("suspected_cause") or "No suspected cause")
    fix = str(analysis.get("suggested_fix") or "No suggested fix")
    confidence = analysis.get("confidence")
    incident_id = str(result.get("incident_id") or "unknown")
    severity = resolve_severity(result)
    if language == "spanish":
        return (
            f"[OpenIncidents] incidente={incident_id} gravedad={severity} confianza={confidence}\n"
            f"resumen: {summary}\n"
            f"causa: {cause}\n"
            f"fix: {fix}"
        )
    return (
        f"[OpenIncidents] incident={incident_id} severity={severity} confidence={confidence}\n"
        f"summary: {summary}\n"
        f"cause: {cause}\n"
        f"fix: {fix}"
    )


def build_jira_description(result: dict[str, Any], *, language: str) -> str:
    analysis = result.get("analysis") or {}
    if language == "spanish":
        lines = [
            f"ID Incidente: {result.get('incident_id', 'unknown')}",
            f"Servicio: {result.get('service', 'unknown-service')}",
            f"Gravedad: {resolve_severity(result)}",
            f"Proveedor: {result.get('provider', 'unknown')}",
            f"Modelo: {result.get('model', 'unknown')}",
            "",
            f"Resumen: {analysis.get('summary', '')}",
            f"Causa sospechada: {analysis.get('suspected_cause', '')}",
            f"Fix sugerido: {analysis.get('suggested_fix', '')}",
            f"Confianza: {analysis.get('confidence', 0)}",
            f"Seguro de escalar: {analysis.get('safe_to_escalate', False)}",
        ]
    else:
        lines = [
            f"Incident ID: {result.get('incident_id', 'unknown')}",
            f"Service: {result.get('service', 'unknown-service')}",
            f"Severity: {resolve_severity(result)}",
            f"Provider: {result.get('provider', 'unknown')}",
            f"Model: {result.get('model', 'unknown')}",
            "",
            f"Summary: {analysis.get('summary', '')}",
            f"Suspected cause: {analysis.get('suspected_cause', '')}",
            f"Suggested fix: {analysis.get('suggested_fix', '')}",
            f"Confidence: {analysis.get('confidence', 0)}",
            f"Safe to escalate: {analysis.get('safe_to_escalate', False)}",
        ]
    return "\n".join(lines)


def build_discord_payload(result: dict[str, Any], *, language: str) -> dict[str, Any]:
    analysis = result.get("analysis") or {}
    severity = resolve_severity(result)
    confidence = analysis.get("confidence")
    summary = str(analysis.get("summary") or "No summary")
    cause = str(analysis.get("suspected_cause") or "No suspected cause")
    fix = str(analysis.get("suggested_fix") or "No suggested fix")
    tests = analysis.get("tests_to_run") or []
    files = analysis.get("files_or_area_to_check") or []
    tests_text = "\n".join(f"- {item}" for item in tests[:4]) if isinstance(tests, list) and tests else "N/A"
    files_text = "\n".join(f"- {item}" for item in files[:4]) if isinstance(files, list) and files else "N/A"
    if language == "spanish":
        title = f"[{severity}] Incidente {result.get('incident_id', 'unknown')}"
        description = f"**Resumen**\n{summary}"
        service_label = "**Servicio**"
        severity_label = "**Gravedad**"
        confidence_label = "**Confianza**"
        cause_label = "**Causa sospechada**"
        fix_label = "**Fix sugerido**"
        files_label = "**Archivos / Areas**"
        tests_label = "**Pruebas sugeridas**"
        footer = f"proveedor={result.get('provider', 'unknown')} modelo={result.get('model', 'unknown')}"
        content = "**Alerta OpenIncidents**"
    else:
        title = f"[{severity}] Incident {result.get('incident_id', 'unknown')}"
        description = f"**Summary**\n{summary}"
        service_label = "**Service**"
        severity_label = "**Severity**"
        confidence_label = "**Confidence**"
        cause_label = "**Suspected Cause**"
        fix_label = "**Suggested Fix**"
        files_label = "**Files / Areas**"
        tests_label = "**Suggested Tests**"
        footer = f"provider={result.get('provider', 'unknown')} model={result.get('model', 'unknown')}"
        content = "**OpenIncidents Alert**"
    embed = {
        "title": title,
        "description": description,
        "color": SEVERITY_COLOR.get(severity, SEVERITY_COLOR["UNKNOWN"]),
        "fields": [
            {"name": service_label, "value": str(result.get("service") or "unknown-service"), "inline": True},
            {"name": severity_label, "value": severity, "inline": True},
            {"name": confidence_label, "value": str(confidence), "inline": True},
            {"name": cause_label, "value": trim_for_field(cause), "inline": False},
            {"name": fix_label, "value": trim_for_field(fix), "inline": False},
            {"name": files_label, "value": trim_for_field(files_text), "inline": False},
            {"name": tests_label, "value": trim_for_field(tests_text), "inline": False},
        ],
        "footer": {
            "text": footer
        },
    }
    return {"content": content, "embeds": [embed]}


def trim_for_field(value: str, limit: int = 1000) -> str:
    text = str(value or "").strip()
    if not text:
        return "N/A"
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def resolve_severity(result: dict[str, Any]) -> str:
    raw = str(result.get("severity") or "").strip().upper()
    if raw in SEVERITY_ORDER:
        return raw
    analysis = result.get("analysis")
    if isinstance(analysis, dict):
        probe = " ".join(
            [
                str(analysis.get("summary") or ""),
                str(analysis.get("suspected_cause") or ""),
            ]
        ).lower()
        if "critical" in probe or "panic" in probe:
            return "CRITICAL"
        if "error" in probe or "timeout" in probe or "failed" in probe:
            return "ERROR"
        if "warn" in probe:
            return "WARNING"
        if probe.strip():
            return "INFO"
    return "UNKNOWN"


def severity_weight(severity: str) -> int:
    return SEVERITY_ORDER.get(str(severity).upper(), 0)


def resolve_language(env: dict[str, str], analysis_payload: dict[str, Any]) -> str:
    configured = str(env.get("TRIAGE_LANGUAGE", "")).strip().lower()
    if configured in ("english", "spanish"):
        return configured
    from_payload = str(analysis_payload.get("language") or "").strip().lower()
    if from_payload in ("english", "spanish"):
        return from_payload
    return "english"


def send_webhook(target: str, url: str, payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    return send_http_json(target, url, payload, headers={}, dry_run=dry_run)


def send_http_json(
    target: str,
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {"target": target, "status": "simulated", "url": url, "payload": payload}
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/plain, */*")
    request.add_header(
        "User-Agent",
        "OpenIncidents-Triage/1.0 (+https://github.com/xperro/OpenIncidents)",
    )
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(getattr(response, "status", 200) or 200)
            content = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "target": target,
            "status": "failed",
            "http_status": int(exc.code),
            "error": detail[:500],
        }
    except urllib.error.URLError as exc:
        return {"target": target, "status": "failed", "error": str(exc.reason)}
    return {"target": target, "status": "sent", "http_status": status, "response_excerpt": content[:300]}
