from __future__ import annotations


def build_payload(summary: dict[str, object]) -> dict[str, str]:
    return {"text": f"{summary['handler']} {summary['cloud']} {summary['payload_length']}"}
