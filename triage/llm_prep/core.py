"""Prepare raw cloud log payloads into compact, redacted LLM-ready incidents."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..constants import VALID_SEVERITIES
from ..errors import UserError


SEVERITY_INDEX = {name: idx for idx, name in enumerate(VALID_SEVERITIES)}
SUMMARY_KEYS = ("message", "summary", "error", "err", "exception", "detail", "details")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-+/=]{8,}\b")
SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b\s*[:=]\s*([^\s,;]+)")
LONG_ID_RE = re.compile(r"\b[A-Za-z0-9_\-]{28,}\b")


@dataclass
class NormalizedEvent:
    cloud: str
    runtime_hint: str
    source: str
    service: str
    env: str
    severity: str
    timestamp: str
    summary: str
    stacktrace: str
    raw_excerpt: str
    source_link: str
    fingerprint: str


def prepare_for_llm(
    raw_payload: str,
    *,
    cloud: str = "auto",
    runtime_hint: str = "auto",
    severity_min: str = "ERROR",
    max_incidents: int = 20,
    max_context_chars: int = 4000,
    max_stack_lines: int = 20,
) -> dict[str, Any]:
    parsed = parse_json_or_raise(raw_payload)
    raw_events = extract_events(parsed, cloud_hint=cloud)
    normalized: list[NormalizedEvent] = []
    dropped = 0

    for raw_event in raw_events:
        event = normalize_event(raw_event, cloud_hint=cloud, runtime_hint=runtime_hint)
        if not should_keep(event, severity_min):
            dropped += 1
            continue
        normalized.append(
            redact_and_truncate(
                event,
                max_context_chars=max_context_chars,
                max_stack_lines=max_stack_lines,
            )
        )

    grouped = group_events(normalized)
    incidents = sorted(grouped.values(), key=incident_sort_key, reverse=True)[:max_incidents]
    prepared_at = datetime.now(timezone.utc).isoformat()
    request_id = f"prep-{uuid.uuid4().hex[:12]}"
    return {
        "schema_version": "llm-prep.v1",
        "request_id": request_id,
        "prepared_at": prepared_at,
        "meta": {
            "input_events": len(raw_events),
            "kept_events": len(normalized),
            "dropped_events": dropped,
            "prepared_incidents": len(incidents),
            "severity_min": severity_min,
            "cloud_hint": cloud,
            "runtime_hint": runtime_hint,
        },
        "incidents": incidents,
    }


def parse_json_or_raise(raw_payload: str) -> Any:
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise UserError(f"Input payload must be valid JSON: {exc}") from exc


def extract_events(value: Any, *, cloud_hint: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for item in value:
            items.extend(extract_events(item, cloud_hint=cloud_hint))
        return items
    if not isinstance(value, dict):
        return []

    if "message" in value and isinstance(value["message"], dict) and isinstance(value["message"].get("data"), str):
        log_entry = decode_gcp_pubsub_log(value["message"]["data"])
        return [log_entry] if log_entry else []
    if "awslogs" in value and isinstance(value["awslogs"], dict) and isinstance(value["awslogs"].get("data"), str):
        return decode_aws_cloudwatch_subscription(value["awslogs"]["data"])
    if "Records" in value and isinstance(value["Records"], list):
        records: list[dict[str, Any]] = []
        for item in value["Records"]:
            records.extend(extract_events(item, cloud_hint=cloud_hint))
        return records
    if "records" in value and isinstance(value["records"], list):
        records = []
        for item in value["records"]:
            records.extend(extract_events(item, cloud_hint=cloud_hint))
        return records
    return [value]


def decode_gcp_pubsub_log(data: str) -> dict[str, Any]:
    try:
        decoded = base64.b64decode(data)
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def decode_aws_cloudwatch_subscription(data: str) -> list[dict[str, Any]]:
    try:
        inflated = gzip.decompress(base64.b64decode(data))
        payload = json.loads(inflated.decode("utf-8"))
    except (ValueError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []

    log_group = str(payload.get("logGroup") or "")
    owner = str(payload.get("owner") or "")
    records: list[dict[str, Any]] = []
    for log_event in payload.get("logEvents", []) or []:
        if not isinstance(log_event, dict):
            continue
        message = str(log_event.get("message") or "")
        record: dict[str, Any] = {
            "source": "cloudwatch_logs",
            "logGroup": log_group,
            "owner": owner,
            "severity": infer_severity(message),
            "timestamp": epoch_millis_to_iso(log_event.get("timestamp")),
            "textPayload": message,
        }
        parsed_message = try_parse_json_object(message)
        if parsed_message:
            record["jsonPayload"] = parsed_message
            record["severity"] = str(parsed_message.get("severity") or record["severity"]).upper()
        records.append(record)
    return records


def try_parse_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw or not raw.startswith("{"):
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def normalize_event(
    event: dict[str, Any],
    *,
    cloud_hint: str,
    runtime_hint: str,
) -> NormalizedEvent:
    cloud = resolve_cloud(event, cloud_hint)
    source = resolve_source(event, cloud)
    service = resolve_service(event, cloud)
    env = resolve_env(event)
    summary = extract_summary(event)
    stacktrace = extract_stacktrace(event)
    severity = resolve_severity(event, summary)
    timestamp = resolve_timestamp(event)
    source_link = build_source_link(event, cloud)
    raw_excerpt = json.dumps(event, ensure_ascii=False)[:4000]
    fingerprint = build_fingerprint(service, severity, summary)
    return NormalizedEvent(
        cloud=cloud,
        runtime_hint=runtime_hint if runtime_hint != "auto" else "unknown",
        source=source,
        service=service,
        env=env,
        severity=severity,
        timestamp=timestamp,
        summary=summary,
        stacktrace=stacktrace,
        raw_excerpt=raw_excerpt,
        source_link=source_link,
        fingerprint=fingerprint,
    )


def resolve_cloud(event: dict[str, Any], hint: str) -> str:
    if hint in ("gcp", "aws"):
        return hint
    if "logName" in event or "resource" in event:
        return "gcp"
    if "logGroup" in event or event.get("source") == "cloudwatch_logs":
        return "aws"
    return "unknown"


def resolve_source(event: dict[str, Any], cloud: str) -> str:
    if cloud == "gcp":
        return "cloud_logging"
    if cloud == "aws":
        return "cloudwatch_logs"
    return str(event.get("source") or "unknown")


def resolve_service(event: dict[str, Any], cloud: str) -> str:
    if cloud == "gcp":
        for candidate in (
            nested_get(event, "resource", "labels", "service_name"),
            nested_get(event, "labels", "run.googleapis.com/service_name"),
            nested_get(event, "jsonPayload", "repo_name"),
            nested_get(event, "jsonPayload", "repository"),
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    if cloud == "aws":
        log_group = str(event.get("logGroup") or "")
        if log_group:
            return log_group.rsplit("/", 1)[-1]
    return "unknown-service"


def resolve_env(event: dict[str, Any]) -> str:
    for candidate in (
        nested_get(event, "labels", "env"),
        nested_get(event, "resource", "labels", "namespace_name"),
        nested_get(event, "jsonPayload", "env"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "unknown"


def resolve_severity(event: dict[str, Any], summary: str) -> str:
    candidate = str(event.get("severity") or nested_get(event, "jsonPayload", "severity") or "").upper()
    if candidate in SEVERITY_INDEX:
        return candidate
    return infer_severity(summary)


def infer_severity(text: str) -> str:
    probe = text.lower()
    if "fatal" in probe or "panic" in probe:
        return "CRITICAL"
    if "error" in probe or "exception" in probe or "traceback" in probe:
        return "ERROR"
    if "warn" in probe:
        return "WARNING"
    return "INFO"


def resolve_timestamp(event: dict[str, Any]) -> str:
    for key in ("timestamp", "receiveTimestamp", "time"):
        raw = event.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return datetime.now(timezone.utc).isoformat()


def extract_summary(event: dict[str, Any]) -> str:
    text_payload = event.get("textPayload")
    if isinstance(text_payload, str) and text_payload.strip():
        return text_payload.strip()
    for root in (event.get("jsonPayload"), event.get("protoPayload"), event):
        found = find_message(root)
        if found:
            return found
    return "No summary available"


def extract_stacktrace(event: dict[str, Any]) -> str:
    for candidate in (
        nested_get(event, "jsonPayload", "stacktrace"),
        nested_get(event, "jsonPayload", "traceback"),
        nested_get(event, "jsonPayload", "exception"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def find_message(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            found = find_message(item)
            if found:
                return found
        return ""
    if isinstance(value, dict):
        for key in SUMMARY_KEYS:
            found = find_message(value.get(key))
            if found:
                return found
        for item in value.values():
            found = find_message(item)
            if found:
                return found
    return ""


def build_source_link(event: dict[str, Any], cloud: str) -> str:
    if cloud == "gcp":
        log_name = str(event.get("logName") or "")
        project = log_name.split("/")[1] if log_name.startswith("projects/") else ""
        if project:
            return f"https://console.cloud.google.com/logs/query;project={project}"
    return ""


def build_fingerprint(service: str, severity: str, summary: str) -> str:
    normalized = re.sub(r"\s+", " ", summary.strip().lower())
    material = f"{service}|{severity}|{normalized}"
    return hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


def should_keep(event: NormalizedEvent, severity_min: str) -> bool:
    severity_floor = severity_min if severity_min in SEVERITY_INDEX else "ERROR"
    return SEVERITY_INDEX.get(event.severity, 0) >= SEVERITY_INDEX[severity_floor]


def redact_and_truncate(
    event: NormalizedEvent,
    *,
    max_context_chars: int,
    max_stack_lines: int,
) -> NormalizedEvent:
    summary = redact_text(event.summary)[:max_context_chars]
    raw_excerpt = redact_text(event.raw_excerpt)[:max_context_chars]
    stack = truncate_stacktrace(redact_text(event.stacktrace), max_stack_lines, max_context_chars)
    return NormalizedEvent(
        cloud=event.cloud,
        runtime_hint=event.runtime_hint,
        source=event.source,
        service=event.service,
        env=event.env,
        severity=event.severity,
        timestamp=event.timestamp,
        summary=summary,
        stacktrace=stack,
        raw_excerpt=raw_excerpt,
        source_link=event.source_link,
        fingerprint=event.fingerprint,
    )


def redact_text(text: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = BEARER_RE.sub(r"\1 [REDACTED_TOKEN]", redacted)
    redacted = SECRET_RE.sub(r"\1=[REDACTED]", redacted)
    redacted = LONG_ID_RE.sub("[REDACTED_VALUE]", redacted)
    return redacted


def truncate_stacktrace(stacktrace: str, max_lines: int, max_chars: int) -> str:
    if not stacktrace:
        return ""
    lines = stacktrace.splitlines()[:max_lines]
    clipped = "\n".join(lines)
    return clipped[:max_chars]


def group_events(events: list[NormalizedEvent]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        bucket = grouped.get(event.fingerprint)
        if bucket is None:
            grouped[event.fingerprint] = {
                "incident_id": event.fingerprint,
                "fingerprint": event.fingerprint,
                "cloud": event.cloud,
                "runtime_hint": event.runtime_hint,
                "source": event.source,
                "service": event.service,
                "env": event.env,
                "severity": event.severity,
                "count": 1,
                "window": {"first_seen": event.timestamp, "last_seen": event.timestamp},
                "summary": event.summary,
                "error_message": event.summary,
                "stacktrace_excerpt": event.stacktrace,
                "source_link": event.source_link,
                "repo_context": [],
                "analysis_mode": "pre_repo",
                "llm_input": {
                    "incident_summary": event.summary,
                    "evidence": [event.raw_excerpt],
                    "constraints": {
                        "max_context_chars": len(event.raw_excerpt),
                        "max_tokens": 1200,
                        "redaction_applied": True,
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
                            "likely_fault_location",
                            "confidence_reason",
                        ],
                    },
                },
            }
            continue
        bucket["count"] += 1
        bucket["window"]["last_seen"] = max(bucket["window"]["last_seen"], event.timestamp)
        if SEVERITY_INDEX.get(event.severity, 0) > SEVERITY_INDEX.get(str(bucket["severity"]), 0):
            bucket["severity"] = event.severity
        evidence = bucket["llm_input"]["evidence"]
        if len(evidence) < 4 and event.raw_excerpt not in evidence:
            evidence.append(event.raw_excerpt)
    return grouped


def incident_sort_key(incident: dict[str, Any]) -> tuple[int, int, str]:
    severity = str(incident.get("severity") or "INFO")
    count = int(incident.get("count") or 0)
    return (SEVERITY_INDEX.get(severity, 0), count, str(incident.get("window", {}).get("last_seen") or ""))


def nested_get(value: dict[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def epoch_millis_to_iso(raw: Any) -> str:
    try:
        millis = int(raw)
        return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()
