"""Placeholder HTTP application module for Cloud Run."""


def handle_request(_request=None):
    return {"status": "ok", "runtime": "python", "cloud": "gcp"}
