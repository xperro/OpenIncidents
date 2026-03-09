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
    env: dict[str, str] | None = None,
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
    language = str(request_payload.get("language") or "english").strip().lower()
    if language not in ("english", "spanish"):
        language = "english"

    key_env = api_key_env or default_api_key_env(chosen_provider)
    env_source = env if env is not None else os.environ
    api_key = env_source.get(key_env, "") if key_env else ""
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
            analysis = mock_analysis(incident, language=language)
            raw_output = json.dumps(analysis)
        elif chosen_provider == "openai":
            raw_output = call_openai(api_key, chosen_model, incident, language=language, timeout_seconds=timeout_seconds)
            analysis = parse_analysis_output(raw_output, incident)
        else:
            raw_output = call_anthropic(api_key, chosen_model, incident, language=language, timeout_seconds=timeout_seconds)
            analysis = parse_analysis_output(raw_output, incident)
        results.append(
            {
                "incident_id": incident_id,
                "provider": chosen_provider,
                "model": chosen_model,
                "service": str(incident.get("service") or "unknown-service"),
                "severity": str(incident.get("severity") or "UNKNOWN"),
                "incident_summary": str(incident.get("incident_summary") or ""),
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
        "language": language,
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
        return "gpt-4o-mini"
    if provider == "anthropic":
        return "claude-3-7-sonnet"
    return "mock-1"


def call_openai(api_key: str, model: str, incident: dict[str, Any], *, language: str, timeout_seconds: int) -> str:
    max_tokens = 700
    constraints = incident.get("constraints")
    if isinstance(constraints, dict):
        try:
            parsed = int(constraints.get("max_tokens") or 700)
            if parsed > 0:
                max_tokens = min(parsed, 1200)
        except (TypeError, ValueError):
            pass
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt(language)},
            {"role": "user", "content": user_prompt(incident, language)},
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


def call_anthropic(api_key: str, model: str, incident: dict[str, Any], *, language: str, timeout_seconds: int) -> str:
    payload = {
        "model": model,
        "max_tokens": 1000,
        "system": system_prompt(language),
        "messages": [{"role": "user", "content": user_prompt(incident, language)}],
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


def system_prompt(language: str) -> str:
    lang_instruction = (
        "Write all textual values in Spanish."
        if language == "spanish"
        else "Write all textual values in English."
    )
    return (
        "You are an incident triage assistant. Return STRICT compact JSON only with fields: "
        "summary, suspected_cause, suggested_fix, confidence, safe_to_escalate, "
        "files_or_area_to_check, tests_to_run, likely_fault_location, confidence_reason. "
        "Use at most 2 items in files_or_area_to_check and tests_to_run. "
        "likely_fault_location must be an object with file, line, function. "
        "Do not add markdown. Keep all values concise. "
        + lang_instruction
    )


def user_prompt(incident: dict[str, Any], language: str) -> str:
    runtime = str(incident.get("runtime_hint") or "").strip().lower()
    label = (
        "Analyze this prepared incident JSON and propose a fix in Spanish:\n"
        if language == "spanish"
        else "Analyze this prepared incident JSON and propose a fix in English:\n"
    )
    runtime_instruction = ""
    if runtime == "go":
        runtime_instruction = (
            "For Go incidents, suggest a concrete fix pattern using explicit nil checks and guard clauses "
            "(example style: if x == nil { return err }). Keep it short.\n"
        )
    elif runtime == "python":
        runtime_instruction = (
            "For Python incidents, suggest a concrete fix pattern with explicit None checks and early returns "
            "(example style: if value is None: return ...). Keep it short.\n"
        )
    return label + runtime_instruction + json.dumps(incident, ensure_ascii=False)


def mock_analysis(incident: dict[str, Any], *, language: str) -> dict[str, Any]:
    summary = str(incident.get("incident_summary") or incident.get("error_message") or "No summary")
    severity = str(incident.get("severity") or "INFO")
    service = str(incident.get("service") or "unknown-service")
    if language == "spanish":
        return {
            "summary": f"{service}: {summary}",
            "suspected_cause": "Posible problema de codigo o dependencia inferido desde la evidencia.",
            "suggested_fix": "Revisar cambios recientes en el flujo afectado, validar salud de dependencias y ajustar retries/timeouts.",
            "confidence": 0.52 if severity == "ERROR" else 0.68,
            "safe_to_escalate": severity in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY"),
            "files_or_area_to_check": [],
            "tests_to_run": ["unitarias", "integracion"],
            "likely_fault_location": {"file": "", "line": 0, "function": ""},
            "confidence_reason": "Diagnostico preliminar basado en resumen y evidencia reducida.",
        }
    return {
        "summary": f"{service}: {summary}",
        "suspected_cause": "Service dependency or application code issue inferred from prepared evidence.",
        "suggested_fix": "Review recent changes around the failing path, validate dependency health, and add retries/timeouts as needed.",
        "confidence": 0.52 if severity == "ERROR" else 0.68,
        "safe_to_escalate": severity in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY"),
        "files_or_area_to_check": [],
        "tests_to_run": ["unit", "integration"],
        "likely_fault_location": {"file": "", "line": 0, "function": ""},
        "confidence_reason": "Preliminary diagnosis from compact incident evidence.",
    }


def parse_analysis_output(raw_output: str, incident: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = extract_first_json_object(raw_output)
    if not isinstance(parsed, dict):
        return fallback_analysis(incident, raw_output)
    likely_location = coerce_location_object(parsed.get("likely_fault_location"))
    files_to_check = coerce_list_of_strings(parsed.get("files_or_area_to_check"))[:2]
    files_to_check = normalize_files_or_areas(files_to_check, likely_location)
    return {
        "summary": str(parsed.get("summary") or ""),
        "suspected_cause": str(parsed.get("suspected_cause") or ""),
        "suggested_fix": str(parsed.get("suggested_fix") or ""),
        "confidence": coerce_confidence(parsed.get("confidence")),
        "safe_to_escalate": bool(parsed.get("safe_to_escalate")),
        "files_or_area_to_check": files_to_check,
        "tests_to_run": coerce_list_of_strings(parsed.get("tests_to_run"))[:2],
        "likely_fault_location": likely_location,
        "confidence_reason": str(parsed.get("confidence_reason") or ""),
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
        "likely_fault_location": {"file": "", "line": 0, "function": ""},
        "confidence_reason": "Fallback response due to parse failure.",
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
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized.endswith("%"):
            try:
                percent = float(normalized[:-1].strip())
                normalized = str(percent / 100.0)
            except (TypeError, ValueError):
                normalized = normalized
        confidence_labels = {
            "very high": 0.95,
            "high": 0.85,
            "medium": 0.6,
            "med": 0.6,
            "low": 0.3,
            "very low": 0.1,
        }
        if normalized in confidence_labels:
            return confidence_labels[normalized]
        value = normalized
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


def coerce_location_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        line = value.get("line")
        try:
            line_num = int(line)
        except (TypeError, ValueError):
            line_num = 0
        return {
            "file": str(value.get("file") or ""),
            "line": line_num,
            "function": str(value.get("function") or ""),
        }
    return {"file": "", "line": 0, "function": ""}


def normalize_files_or_areas(files: list[str], likely_location: dict[str, Any]) -> list[str]:
    likely_file = str(likely_location.get("file") or "").strip()
    likely_line = int(likely_location.get("line") or 0)
    if likely_file and likely_line > 0:
        return [likely_file]
    if likely_file:
        if likely_file in files:
            return [likely_file]
        return [likely_file] + files[:1]
    return files[:2]
