"""Infrastructure generation, packaging, and Terraform orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
import zipfile
from typing import Any

from .constants import PLACEHOLDER_CONTAINER_IMAGE, PLACEHOLDER_LAMBDA_PACKAGE
from .errors import UserError
from .project import (
    derive_aws_filter_pattern,
    derive_gcp_log_filter,
    render_json,
    validate_project_config,
    write_file,
)
from .templates import validate_handler_path
from .validation import run_subprocess


def infra_dir(cwd: str, cloud: str) -> str:
    return os.path.join(cwd, ".triage", "infra", cloud)


def build_dir(cwd: str, cloud: str, runtime: str) -> str:
    return os.path.join(cwd, ".triage", "build", cloud, runtime)


def generate_inputs(
    project: dict[str, Any], cloud: str, runtime: str, artifact_reference: str | None = None
) -> dict[str, Any]:
    errors = validate_project_config(project, cloud)
    if errors:
        raise UserError("\n".join(errors))
    if cloud == "gcp":
        gcp = project["gcp"]
        return {
            "project_id": gcp["project_id"],
            "region": gcp["region"],
            "env": project["env"],
            "sink_name": gcp["sink_name"],
            "log_filter": derive_gcp_log_filter(project),
            "topic_name": gcp["topic_name"],
            "subscription_name": gcp["subscription_name"],
            "cloud_run_service_name": gcp["cloud_run_service_name"],
            "artifact_registry_repository": gcp["artifact_registry_repository"],
            "container_image": artifact_reference or PLACEHOLDER_CONTAINER_IMAGE,
            "runtime": runtime,
        }
    aws = project["aws"]
    return {
        "region": aws["region"],
        "env": project["env"],
        "log_group_name": aws["log_group_name"],
        "lambda_name": aws["lambda_name"],
        "lambda_package": artifact_reference or PLACEHOLDER_LAMBDA_PACKAGE,
        "package_format": aws["package_format"],
        "filter_name": aws["filter_name"],
        "filter_pattern": derive_aws_filter_pattern(project),
        "runtime": runtime,
    }


def generate_infra(cwd: str, project: dict[str, Any], cloud: str, runtime: str) -> dict[str, Any]:
    target_dir = infra_dir(cwd, cloud)
    os.makedirs(target_dir, exist_ok=True)
    inputs = generate_inputs(project, cloud, runtime)
    write_file(os.path.join(target_dir, "main.tf"), terraform_main(cloud))
    write_file(os.path.join(target_dir, "variables.tf"), terraform_variables(cloud))
    write_file(
        os.path.join(target_dir, "terraform.tfvars.json"),
        json.dumps(inputs, indent=2, sort_keys=True) + "\n",
    )
    write_file(
        os.path.join(target_dir, "generated.json"),
        render_json({"cloud": cloud, "runtime": runtime, "inputs": inputs}),
    )
    return {"infra_dir": target_dir, "inputs": inputs}


def package_handler(
    cwd: str, cloud: str, runtime: str, handler_path: str
) -> dict[str, Any]:
    validation = validate_handler_path(runtime, cloud, handler_path)
    target_dir = build_dir(cwd, cloud, runtime)
    os.makedirs(target_dir, exist_ok=True)
    if cloud == "gcp":
        artifact_path = os.path.join(target_dir, "triage-handler.tar.gz")
        with tarfile.open(artifact_path, "w:gz") as archive:
            archive.add(handler_path, arcname="triage-handler")
        reference = f"file://{artifact_path}"
    else:
        artifact_path = os.path.join(target_dir, "triage-handler.zip")
        with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(handler_path):
                for filename in files:
                    source = os.path.join(root, filename)
                    relative = os.path.relpath(source, handler_path)
                    archive.write(source, arcname=relative)
        reference = artifact_path
    digest = sha256_file(artifact_path)
    metadata = {
        "cloud": cloud,
        "runtime": runtime,
        "handler_path": handler_path,
        "validated_template": validation,
        "artifact_path": artifact_path,
        "artifact_reference": reference,
        "sha256": digest,
    }
    write_file(os.path.join(target_dir, "artifact.json"), render_json(metadata))
    return metadata


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def terraform_main(cloud: str) -> str:
    if cloud == "gcp":
        return """terraform {
  required_version = ">= 1.5.0"
}

output "pubsub_topic" {
  value = var.topic_name
}

output "pubsub_subscription" {
  value = var.subscription_name
}

output "sink_writer_identity" {
  value = null
}

output "cloud_run_url" {
  value = null
}

output "artifact_registry_repository" {
  value = var.artifact_registry_repository
}

output "deployment_summary" {
  value = {
    cloud           = "gcp"
    runtime         = var.runtime
    log_filter      = var.log_filter
    container_image = var.container_image
  }
}
"""
    return """terraform {
  required_version = ">= 1.5.0"
}

output "lambda_arn" {
  value = null
}

output "subscription_filter_name" {
  value = var.filter_name
}

output "deployment_summary" {
  value = {
    cloud          = "aws"
    runtime        = var.runtime
    filter_pattern = var.filter_pattern
    lambda_package = var.lambda_package
  }
}
"""


def terraform_variables(cloud: str) -> str:
    if cloud == "gcp":
        names = (
            "project_id",
            "region",
            "env",
            "sink_name",
            "log_filter",
            "topic_name",
            "subscription_name",
            "cloud_run_service_name",
            "artifact_registry_repository",
            "container_image",
            "runtime",
        )
    else:
        names = (
            "region",
            "env",
            "log_group_name",
            "lambda_name",
            "lambda_package",
            "package_format",
            "filter_name",
            "filter_pattern",
            "runtime",
        )
    return "\n\n".join(
        f'variable "{name}" {{\n  type = string\n}}' for name in names
    ) + "\n"


def terraform_plan(cwd: str, cloud: str, runtime: str) -> dict[str, Any]:
    target_dir = infra_dir(cwd, cloud)
    if not os.path.isdir(target_dir):
        raise UserError(
            f"Infrastructure directory does not exist yet: {target_dir}. Run `triage infra generate` first."
        )
    output_dir = build_dir(cwd, cloud, runtime)
    os.makedirs(output_dir, exist_ok=True)
    plan_path = os.path.join(output_dir, "triage.tfplan")
    init_result = run_subprocess(
        ["terraform", "init", "-input=false", "-no-color"], cwd=target_dir
    )
    if init_result.returncode != 0:
        raise UserError(init_result.stderr.strip() or init_result.stdout.strip())
    plan_result = run_subprocess(
        ["terraform", "plan", "-input=false", "-no-color", "-out", plan_path],
        cwd=target_dir,
    )
    if plan_result.returncode != 0:
        raise UserError(plan_result.stderr.strip() or plan_result.stdout.strip())
    return {"plan_path": plan_path}


def terraform_apply(cwd: str, cloud: str, runtime: str) -> dict[str, Any]:
    target_dir = infra_dir(cwd, cloud)
    if not os.path.isdir(target_dir):
        raise UserError(
            f"Infrastructure directory does not exist yet: {target_dir}. Run `triage infra generate` first."
        )
    init_result = run_subprocess(
        ["terraform", "init", "-input=false", "-no-color"], cwd=target_dir
    )
    if init_result.returncode != 0:
        raise UserError(init_result.stderr.strip() or init_result.stdout.strip())
    apply_result = run_subprocess(
        ["terraform", "apply", "-input=false", "-no-color", "-auto-approve"],
        cwd=target_dir,
    )
    if apply_result.returncode != 0:
        raise UserError(apply_result.stderr.strip() or apply_result.stdout.strip())
    output_result = run_subprocess(["terraform", "output", "-json"], cwd=target_dir)
    outputs = {}
    if output_result.returncode == 0 and output_result.stdout.strip():
        outputs = json.loads(output_result.stdout)
    metadata = {"cloud": cloud, "runtime": runtime, "outputs": outputs}
    write_file(
        os.path.join(build_dir(cwd, cloud, runtime), "apply.json"),
        render_json(metadata),
    )
    return metadata
