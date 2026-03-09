# triage-handler (python, gcp)

GCP handler template for the OpenIncidents CLI release bundle.

Target Python version: `3.14.3`.

Run the template with a Python `3.14.3` interpreter so local replay, packaging, and Cloud Run validation stay aligned with the current stable CPython release line.

The Cloud Run entrypoint uses `Starlette` plus `uvicorn` and exposes:

- `POST /` for Pub/Sub push delivery
- `GET /healthz` for service health checks
