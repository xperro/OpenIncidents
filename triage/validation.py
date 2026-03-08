"""Live cloud and tooling validation helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ValidationResult:
    cloud: str
    ok: bool
    checks: list[str]


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _run_command(command: list[str], env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def validate_gcp() -> ValidationResult:
    checks = []
    ok = True
    for binary in ("gcloud", "terraform"):
        exists = command_exists(binary)
        checks.append(f"{binary}: {'ok' if exists else 'missing'}")
        ok = ok and exists
    adc_ok = False
    if command_exists("gcloud"):
        result = _run_command(["gcloud", "auth", "application-default", "print-access-token"])
        adc_ok = result.returncode == 0 and bool(result.stdout.strip())
    if not adc_ok:
        candidate = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        adc_ok = bool(candidate and os.path.exists(candidate))
    checks.append(f"application-default-credentials: {'ok' if adc_ok else 'missing'}")
    ok = ok and adc_ok
    return ValidationResult(cloud="gcp", ok=ok, checks=checks)


def validate_aws() -> ValidationResult:
    checks = []
    ok = True
    for binary in ("aws", "terraform"):
        exists = command_exists(binary)
        checks.append(f"{binary}: {'ok' if exists else 'missing'}")
        ok = ok and exists
    identity_ok = False
    if command_exists("aws"):
        result = _run_command(["aws", "sts", "get-caller-identity", "--output", "json"])
        identity_ok = result.returncode == 0
    checks.append(f"sts-get-caller-identity: {'ok' if identity_ok else 'failed'}")
    ok = ok and identity_ok
    return ValidationResult(cloud="aws", ok=ok, checks=checks)


def validate_cloud(cloud: str) -> ValidationResult:
    if cloud == "gcp":
        return validate_gcp()
    if cloud == "aws":
        return validate_aws()
    raise ValueError(f"Unsupported cloud: {cloud}")


def validate_runtime(runtime: str) -> tuple[bool, str]:
    if runtime == "python":
        return True, "python: ok"
    if runtime == "go":
        ok = command_exists("go")
        return ok, f"go: {'ok' if ok else 'missing'}"
    raise ValueError(f"Unsupported runtime: {runtime}")


def run_subprocess(command: list[str], cwd: str | None = None, env=None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        input=input_text,
    )
