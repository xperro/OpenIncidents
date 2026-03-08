from __future__ import annotations


def build_payload(summary: dict[str, object]) -> dict[str, object]:
    return {"fields": {"summary": f"{summary['handler']} {summary['cloud']} incident"}}
