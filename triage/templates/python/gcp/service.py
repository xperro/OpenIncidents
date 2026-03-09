from __future__ import annotations

import base64
import json
import os
import re
from typing import Any


ROUTING_ENV = "TRIAGE_GCP_SINK_ROUTING"
MESSAGE_KEYS = ("message", "summary", "error", "err", "exception", "detail", "details")


def build_summary(
    cloud: str,
    entrypoint: str,
    payload: str | bytes,
    repo_name: str = "",
    sink_name: str = "",
) -> dict[str, object]:
    payload_bytes = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    log_entry = decode_gcp_pubsub_log_entry(payload_bytes)
    resolved_repo_name, resolved_sink_name = classify_gcp_log_entry(log_entry, repo_name, sink_name)
    error_message = extract_clear_error(log_entry)
    summary = {
        "handler": "triage-handler",
        "runtime": "python",
        "cloud": cloud,
        "entrypoint": entrypoint,
        "payload_length": len(payload_bytes),
    }
    if log_entry:
        summary["logging_event"] = log_entry
    if resolved_repo_name:
        summary["repo_name"] = resolved_repo_name
    if resolved_sink_name:
        summary["sink_name"] = resolved_sink_name
    if error_message:
        summary["error_message"] = error_message
    return summary


def decode_gcp_pubsub_log_entry(payload: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    message = envelope.get("message", {})
    data = message.get("data")
    if not isinstance(data, str) or not data:
        return envelope if isinstance(envelope, dict) else {}
    try:
        decoded = base64.b64decode(data)
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def classify_gcp_log_entry(
    log_entry: dict[str, Any], repo_name: str, sink_name: str
) -> tuple[str, str]:
    if repo_name or sink_name:
        return repo_name, sink_name
    searchable = collect_searchable_fields(log_entry)
    for route in load_gcp_sink_routing():
        needle = str(route.get("repo_match_like") or "").strip().lower()
        if needle and any(needle in value for value in searchable):
            return str(route.get("repo_name") or "").strip(), str(route.get("sink_name") or "").strip()
    inferred = infer_repo_name(log_entry)
    return inferred, sink_name


def load_gcp_sink_routing() -> list[dict[str, str]]:
    raw = os.environ.get(ROUTING_ENV, "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    resolved = []
    for item in data:
        if not isinstance(item, dict):
            continue
        resolved.append(
            {
                "sink_name": str(item.get("sink_name") or "").strip(),
                "repo_name": str(item.get("repo_name") or "").strip(),
                "repo_match_like": str(item.get("repo_match_like") or "").strip(),
            }
        )
    return resolved


def collect_searchable_fields(log_entry: dict[str, Any]) -> list[str]:
    values = []
    for candidate in (
        log_entry.get("logName"),
        log_entry.get("textPayload"),
        nested_get(log_entry, "jsonPayload", "message"),
        nested_get(log_entry, "jsonPayload", "repo_name"),
        nested_get(log_entry, "jsonPayload", "repository"),
        nested_get(log_entry, "labels", "run.googleapis.com/service_name"),
        nested_get(log_entry, "resource", "labels", "service_name"),
        nested_get(log_entry, "resource", "labels", "revision_name"),
        nested_get(log_entry, "protoPayload", "resourceName"),
        nested_get(log_entry, "protoPayload", "authenticationInfo", "principalEmail"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            values.append(candidate.strip().lower())
    return values


def infer_repo_name(log_entry: dict[str, Any]) -> str:
    for candidate in (
        nested_get(log_entry, "resource", "labels", "service_name"),
        nested_get(log_entry, "labels", "run.googleapis.com/service_name"),
        nested_get(log_entry, "jsonPayload", "repo_name"),
        nested_get(log_entry, "jsonPayload", "repository"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    text_payload = str(log_entry.get("textPayload") or "")
    match = re.search(r"bitbucket\.org/[^/]+/([^/]+)/pull-requests/\d+", text_payload)
    if match:
        return match.group(1)
    return ""


def extract_clear_error(log_entry: dict[str, Any]) -> str:
    top_level = log_entry.get("textPayload")
    if isinstance(top_level, str) and top_level.strip():
        return top_level.strip()
    for root in (log_entry.get("jsonPayload"), log_entry.get("protoPayload")):
        found = find_message_in_object(root)
        if found:
            return found
    method_name = nested_get(log_entry, "protoPayload", "methodName")
    resource_name = nested_get(log_entry, "protoPayload", "resourceName")
    if isinstance(method_name, str) and isinstance(resource_name, str):
        return f"{method_name} {resource_name}".strip()
    return ""


def find_message_in_object(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            found = find_message_in_object(item)
            if found:
                return found
        return ""
    if isinstance(value, dict):
        for key in MESSAGE_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            found = find_message_in_object(candidate)
            if found:
                return found
        for candidate in value.values():
            found = find_message_in_object(candidate)
            if found:
                return found
    return ""


def nested_get(value: dict[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current
