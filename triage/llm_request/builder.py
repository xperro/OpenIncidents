"""Transform llm-prep output into a canonical LLM request payload."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..errors import UserError


def build_llm_request_payload(
    prepared: dict[str, Any],
    *,
    provider: str,
    model: str,
    language: str = "english",
    max_tokens: int = 1200,
) -> dict[str, Any]:
    if provider not in ("openai", "anthropic", "mock"):
        raise UserError("`--provider` must be `openai`, `anthropic`, or `mock`.")
    if not model.strip():
        raise UserError("`--model` must not be empty.")
    if language not in ("english", "spanish"):
        raise UserError("`language` must be `english` or `spanish`.")
    incidents = prepared.get("incidents")
    if not isinstance(incidents, list):
        raise UserError("Input must contain an `incidents` list (output from `triage llm-prep`).")

    request_id = f"llmreq-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    transformed = []
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        incident_id = str(incident.get("incident_id") or incident.get("fingerprint") or uuid.uuid4().hex[:16])
        llm_input = incident.get("llm_input", {})
        evidence = llm_input.get("evidence", [])
        transformed.append(
            {
                "incident_id": incident_id,
                "service": str(incident.get("service") or "unknown-service"),
                "cloud": str(incident.get("cloud") or "unknown"),
                "runtime_hint": str(incident.get("runtime_hint") or "unknown"),
                "severity": str(incident.get("severity") or "INFO"),
                "count": int(incident.get("count") or 1),
                "window": incident.get("window") or {},
                "incident_summary": str(llm_input.get("incident_summary") or incident.get("summary") or ""),
                "error_message": str(incident.get("error_message") or ""),
                "stacktrace_excerpt": str(incident.get("stacktrace_excerpt") or ""),
                "evidence": evidence if isinstance(evidence, list) else [],
                "source_link": str(incident.get("source_link") or ""),
                "repo_context": incident.get("repo_context") if isinstance(incident.get("repo_context"), list) else [],
                "analysis_mode": str(incident.get("analysis_mode") or "pre_repo"),
                "constraints": {
                    "max_tokens": max_tokens,
                    "redaction_applied": bool(
                        (llm_input.get("constraints") or {}).get("redaction_applied", True)
                    ),
                },
                "response_contract": {
                    "format": "json",
                    "required_fields": [
                        "summary",
                        "suspected_cause",
                        "suggested_fix",
                        "confidence",
                        "safe_to_escalate",
                        "files_or_area_to_check",
                        "tests_to_run",
                    ],
                },
            }
        )

    return {
        "schema_version": "llm-request.v1",
        "request_id": request_id,
        "created_at": created_at,
        "provider": provider,
        "model": model,
        "language": language,
        "incidents": transformed,
        "meta": {
            "source_schema_version": prepared.get("schema_version"),
            "prepared_incidents": len(transformed),
        },
    }
