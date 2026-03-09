"""Local replay orchestration for handler templates."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from .errors import UserError
from .infra import build_dir
from .project import render_json, required_runtime_env_vars, write_file
from .templates import validate_handler_path
from .validation import run_subprocess


def load_env_file(path: str, env: dict[str, str]) -> dict[str, str]:
    if not os.path.exists(path):
        return env
    loaded = dict(env)
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            loaded.setdefault(key.strip(), value.strip())
    return loaded


def read_input(input_path: str, stdin) -> str:
    if input_path == "-":
        is_tty = getattr(stdin, "isatty", None)
        if callable(is_tty) and is_tty():
            raise UserError(
                "No replay payload was provided on stdin. Pipe an event into `triage run` "
                "or pass `--input /abs/path/to/event.json`."
            )
        return stdin.read()
    with open(input_path, "r", encoding="utf-8") as handle:
        return handle.read()


def validate_runtime_env(project: dict[str, Any], env: dict[str, str]) -> None:
    missing = [name for name in required_runtime_env_vars(project) if not env.get(name)]
    if missing:
        raise UserError(
            "Missing environment variables for local run: " + ", ".join(sorted(missing))
        )


def runtime_command(runtime: str, handler_path: str, cloud: str, input_path: str) -> list[str]:
    if runtime == "python":
        main_path = os.path.join(handler_path, "main.py")
        if not os.path.exists(main_path):
            raise UserError(f"Python handler entrypoint not found: {main_path}")
        return [sys.executable, main_path, "--cloud", cloud, "--input", input_path]
    if runtime == "go":
        local_dir = os.path.join(handler_path, "cmd", "triage-handler-local")
        if not os.path.isdir(local_dir):
            raise UserError(f"Go local entrypoint not found: {local_dir}")
        return ["go", "run", "./cmd/triage-handler-local", "--cloud", cloud, "--input", input_path]
    raise UserError(f"Unsupported runtime: {runtime}")


def run_local(
    cwd: str,
    project: dict[str, Any],
    cloud: str,
    runtime: str,
    handler_path: str,
    input_path: str,
    stdin,
) -> dict[str, Any]:
    validate_handler_path(runtime, cloud, handler_path)
    if input_path != "-" and not os.path.isabs(input_path):
        raise UserError("`--input` must be absolute when a file path is provided.")
    env = dict(os.environ)
    env = load_env_file(os.path.join(cwd, ".env"), env)
    env = load_env_file(os.path.join(handler_path, ".env"), env)
    validate_runtime_env(project, env)
    payload = read_input(input_path, stdin)
    command = runtime_command(runtime, handler_path, cloud, input_path)
    result = run_subprocess(command, cwd=handler_path, env=env, input_text=payload if input_path == "-" else None)
    report = {
        "cloud": cloud,
        "runtime": runtime,
        "handler_path": handler_path,
        "input_path": input_path,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    try:
        if report["stdout"]:
            report["stdout_json"] = json.loads(report["stdout"])
    except json.JSONDecodeError:
        pass
    target_dir = build_dir(cwd, "local", runtime)
    os.makedirs(target_dir, exist_ok=True)
    write_file(os.path.join(target_dir, "last-run.json"), render_json(report))
    if result.returncode != 0:
        raise UserError(result.stderr.strip() or "Local handler execution failed.")
    return report
