from __future__ import annotations


def build_summary(cloud: str, entrypoint: str, payload: str | bytes) -> dict[str, object]:
    if isinstance(payload, bytes):
        payload_length = len(payload)
    else:
        payload_length = len(payload)
    return {
        "handler": "triage-handler",
        "runtime": "python",
        "cloud": cloud,
        "entrypoint": entrypoint,
        "payload_length": payload_length,
    }
