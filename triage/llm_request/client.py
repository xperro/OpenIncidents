"""Execute LLM requests and return structured incident analysis."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

from ..errors import UserError


def run_llm_client(
    request_payload: dict[str, Any],
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key_env: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    incidents = request_payload.get("incidents")
    if not isinstance(incidents, list):
        raise UserError("LLM request payload must include an `incidents` list.")

    chosen_provider = (provider or request_payload.get("provider") or "").strip()
    chosen_model = (model or request_payload.get("model") or "").strip()
    if chosen_provider not in ("openai", "anthropic", "mock"):
        raise UserError("Provider must be `openai`, `anthropic`, or `mock`.")
    if not chosen_model:
        chosen_model = default_model(chosen_provider)

    key_env = api_key_env or default_api_key_env(chosen_provider)
    api_key = os.environ.get(key_env, "") if key_env else ""
    if chosen_provider != "mock" and not api_key:
        raise UserError(
            f"Missing API key for provider `{chosen_provider}`. Set environment variable `{key_env}`."
        )

    results = []
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        incident_id = str(incident.get("incident_id") or uuid.uuid4().hex[:16])
        if chosen_provider == "mock":
            analysis = mock_analysis(incident)
            raw_output = json.dumps(analysis)
        elif chosen_provider == "openai":
            raw_output = call_openai(api_key, chosen_model, incident, timeout_seconds=timeout_seconds)
            analysis = parse_analysis_output(raw_output, incident)
        else:
            raw_output = call_anthropic(api_key, chosen_model, incident, timeout_seconds=timeout_seconds)
            analysis = parse_analysis_output(raw_output, incident)
        results.append(
            {
                "incident_id": incident_id,
                "provider": chosen_provider,
                "model": chosen_model,
                "analysis": analysis,
                "raw_output": raw_output,
            }
        )

    return {
        "schema_version": "llm-analysis.v1",
        "request_id": str(request_payload.get("request_id") or f"llman-{uuid.uuid4().hex[:12]}"),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "provider": chosen_provider,
        "model": chosen_model,
        "results": results,
        "meta": {
            "input_incidents": len(incidents),
            "analyzed_incidents": len(results),
        },
    }


def default_api_key_env(provider: str) -> str:
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    return ""


def default_model(provider: str) -> str:
    if provider == "openai":
        return "gpt-4.1"
    if provider == "anthropic":
        return "claude-3-7-sonnet"
    return "mock-1"


def call_openai(api_key: str, model: str, incident: dict[str, Any], *, timeout_seconds: int) -> str:
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(incident)},
        ],
    }
    response = http_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout_seconds=timeout_seconds,
    )
    try:
        return str(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return json.dumps(response)


def call_anthropic(api_key: str, model: str, incident: dict[str, Any], *, timeout_seconds: int) -> str:
    payload = {
        "model": model,
        "max_tokens": 1000,
        "system": system_prompt(),
        "messages": [{"role": "user", "content": user_prompt(incident)}],
    }
    response = http_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout_seconds=timeout_seconds,
    )
    content = response.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("text") or json.dumps(first))
    return json.dumps(response)


def http_json(url: str, payload: dict[str, Any], *, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise UserError(f"LLM provider request failed ({exc.code}): {detail}")
    except urllib.error.URLError as exc:
        raise UserError(f"LLM provider request failed: {exc.reason}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise UserError("LLM provider returned non-JSON response.")
    if not isinstance(parsed, dict):
        raise UserError("LLM provider returned unexpected payload shape.")
    return parsed


def system_prompt() -> str:
    return (
        "You are an incident triage assistant. Return STRICT JSON only with fields: "
        "summary, suspected_cause, suggested_fix, confidence, safe_to_escalate, "
        "files_or_area_to_check, tests_to_run. "
        "Do not add markdown."
    )


def user_prompt(incident: dict[str, Any]) -> str:
    return "Analyze this prepared incident JSON and propose a fix:\n" + json.dumps(incident, ensure_ascii=False)


def mock_analysis(incident: dict[str, Any]) -> dict[str, Any]:
    summary = str(incident.get("incident_summary") or incident.get("error_message") or "No summary")
    severity = str(incident.get("severity") or "INFO")
    service = str(incident.get("service") or "unknown-service")
    return {
        "summary": f"{service}: {summary}",
        "suspected_cause": "Service dependency or application code issue inferred from prepared evidence.",
        "suggested_fix": "Review recent changes around the failing path, validate dependency health, and add retries/timeouts as needed.",
        "confidence": 0.52 if severity == "ERROR" else 0.68,
        "safe_to_escalate": severity in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY"),
        "files_or_area_to_check": [],
        "tests_to_run": ["unit", "integration"],
    }


def parse_analysis_output(raw_output: str, incident: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = extract_first_json_object(raw_output)
    if not isinstance(parsed, dict):
        return fallback_analysis(incident, raw_output)
    return {
        "summary": str(parsed.get("summary") or ""),
        "suspected_cause": str(parsed.get("suspected_cause") or ""),
        "suggested_fix": str(parsed.get("suggested_fix") or ""),
        "confidence": coerce_confidence(parsed.get("confidence")),
        "safe_to_escalate": bool(parsed.get("safe_to_escalate")),
        "files_or_area_to_check": coerce_list_of_strings(parsed.get("files_or_area_to_check")),
        "tests_to_run": coerce_list_of_strings(parsed.get("tests_to_run")),
    }


def fallback_analysis(incident: dict[str, Any], raw_output: str) -> dict[str, Any]:
    summary = str(incident.get("incident_summary") or incident.get("error_message") or "No summary")
    return {
        "summary": summary,
        "suspected_cause": "Model response could not be parsed as strict JSON.",
        "suggested_fix": "Retry analysis with narrower context and stricter response format.",
        "confidence": 0.0,
        "safe_to_escalate": False,
        "files_or_area_to_check": [],
        "tests_to_run": [],
        "parse_error_excerpt": raw_output[:400],
    }


def extract_first_json_object(raw: str) -> dict[str, Any] | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    snippet = raw[start : end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def coerce_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def coerce_list_of_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
