"""Real handler template discovery, copy, and validation helpers."""

from __future__ import annotations

from importlib import resources
import os
import pathlib
import shutil
import sys
from typing import Any

from .errors import UserError

SKIP_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    ".git",
}
SKIP_SUFFIXES = (".pyc", ".pyo", ".swp", ".tmp")

REQUIRED_PATHS: dict[tuple[str, str], tuple[str, ...]] = {
    ("go", "gcp"): ("go.mod", "go.sum", "cmd/triage-handler", "cmd/triage-handler-local"),
    ("go", "aws"): ("go.mod", "go.sum", "cmd/triage-handler-lambda", "cmd/triage-handler-local"),
    ("python", "gcp"): ("requirements.txt", "main.py", "app.py", "adapters/gcp.py", "adapters/local.py"),
    ("python", "aws"): (
        "requirements.txt",
        "main.py",
        "lambda_entrypoint.py",
        "adapters/aws.py",
        "adapters/local.py",
    ),
}


def resolve_templates_root() -> str:
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "templates")),
        os.path.abspath(
            os.path.join(os.path.dirname(os.path.realpath(sys.argv[0] or "")), "triage", "templates")
        ),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    raise UserError("Physical template root not found.")


def resolve_template_source_root() -> tuple[str, Any]:
    try:
        root = resolve_templates_root()
        return root, pathlib.Path(root)
    except UserError:
        package_root = resources.files("triage").joinpath("templates")
        if package_root.is_dir():
            return "embedded:triage/templates", package_root
    raise UserError(
        "Template root not found. Expected `triage/templates/` inside the CLI source tree "
        "or embedded in `triage.pyz` in the release bundle."
    )


def template_variant_source(cloud: str, runtime: str) -> tuple[str, Any]:
    root_display, root = resolve_template_source_root()
    return root_display, root.joinpath(runtime).joinpath(cloud)


def validate_handler_path(runtime: str, cloud: str, handler_path: str) -> dict[str, Any]:
    if not os.path.isabs(handler_path):
        raise UserError("`--handler-path` must be absolute.")
    if not os.path.isdir(handler_path):
        raise UserError(f"Handler path does not exist: {handler_path}")

    required = REQUIRED_PATHS.get((runtime, cloud))
    if required is None:
        raise UserError(f"Unsupported template variant: runtime={runtime}, cloud={cloud}")

    missing = []
    for relative in required:
        if not os.path.exists(os.path.join(handler_path, relative)):
            missing.append(relative)

    if missing:
        raise UserError(
            f"`--handler-path` does not match the expected {runtime}/{cloud} template variant. Missing: "
            + ", ".join(missing)
        )

    return {
        "handler_path": handler_path,
        "runtime": runtime,
        "cloud": cloud,
        "required_paths": list(required),
    }


def download_template(cloud: str, runtime: str, output_path: str, force: bool) -> dict[str, Any]:
    if not os.path.isabs(output_path):
        raise UserError("`--output` must be an absolute path.")
    if os.path.exists(output_path) and not os.path.isdir(output_path):
        raise UserError("`--output` must point to a directory path.")

    source_root_display, source_dir = template_variant_source(cloud, runtime)
    if not source_dir.is_dir():
        raise UserError(f"Template variant not found: {source_root_display}/{runtime}/{cloud}")

    if os.path.isdir(output_path):
        existing = os.listdir(output_path)
        if existing and not force:
            raise UserError(
                "Output directory is not empty. Re-run with `--force` to overwrite template files."
            )
        if existing and force:
            shutil.rmtree(output_path)

    os.makedirs(output_path, exist_ok=True)
    written = copy_template_tree(source_dir, output_path)

    return {
        "cloud": cloud,
        "runtime": runtime,
        "output_path": output_path,
        "source_path": f"{source_root_display}/{runtime}/{cloud}",
        "written_files": written,
    }


def copy_template_tree(source_dir: Any, output_path: str) -> list[str]:
    written: list[str] = []

    def copy_node(source_node: Any, target_dir: str) -> None:
        os.makedirs(target_dir, exist_ok=True)
        for child in sorted(source_node.iterdir(), key=lambda entry: entry.name):
            if should_skip_name(child.name):
                continue
            target_path = os.path.join(target_dir, child.name)
            if child.is_dir():
                copy_node(child, target_path)
                continue
            with child.open("rb") as source_handle, open(target_path, "wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
            written.append(os.path.abspath(target_path))

    copy_node(source_dir, output_path)
    return sorted(written)


def should_skip_name(name: str) -> bool:
    if name in SKIP_NAMES:
        return True
    return any(name.endswith(suffix) for suffix in SKIP_SUFFIXES)
