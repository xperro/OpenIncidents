"""Starlette application module for Cloud Run."""

from __future__ import annotations

import os

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from service import build_summary


async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "runtime": "python", "cloud": "gcp"})


async def handle_push(request: Request) -> JSONResponse:
    payload = await request.body()
    return JSONResponse(
        build_summary(
            "gcp",
            "cloud-run-http",
            payload,
            repo_name=request.query_params.get("repo_name", ""),
            sink_name=request.query_params.get("sink_name", ""),
        )
    )


app = Starlette(routes=[Route("/", handle_push, methods=["POST"]), Route("/healthz", healthz)])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
