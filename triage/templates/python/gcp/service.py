from __future__ import annotations


def build_summary(cloud: str, entrypoint: str, payload: str) -> dict[str, object]:
    return {
        "handler": "triage-handler",
        "runtime": "python",
        "cloud": cloud,
        "entrypoint": entrypoint,
        "payload_length": len(payload),
    }
