"""Infrastructure generation, packaging, and Terraform orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import zipfile
from typing import Any

from .constants import PLACEHOLDER_LAMBDA_PACKAGE, VERSION
from .errors import UserError
from .project import (
    derive_aws_filter_pattern,
    derive_gcp_sinks,
    normalize_env_slug,
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


def run_checked(command: list[str], cwd: str | None = None, env=None) -> str:
    result = run_subprocess(command, cwd=cwd, env=env)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Command failed."
        raise UserError(detail)
    return result.stdout


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
            "topic_name": gcp["topic_name"],
            "subscription_name": gcp["subscription_name"],
            "sinks": derive_gcp_sinks(project),
            "cloud_run_service_name": gcp["cloud_run_service_name"],
            "artifact_registry_repository": gcp["artifact_registry_repository"],
            "container_image": artifact_reference or gcp_placeholder_image_reference(project, runtime),
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
    cwd: str, cloud: str, runtime: str, handler_path: str, project: dict[str, Any] | None = None
) -> dict[str, Any]:
    validation = validate_handler_path(runtime, cloud, handler_path)
    target_dir = build_dir(cwd, cloud, runtime)
    os.makedirs(target_dir, exist_ok=True)
    if cloud == "gcp":
        if project is None:
            raise UserError("Project config is required to package the GCP handler.")
        metadata = package_gcp_handler(cwd, target_dir, runtime, handler_path, validation, project)
        write_file(os.path.join(target_dir, "artifact.json"), render_json(metadata))
        return metadata
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


def package_gcp_handler(
    cwd: str,
    target_dir: str,
    runtime: str,
    handler_path: str,
    validation: dict[str, Any],
    project: dict[str, Any],
) -> dict[str, Any]:
    bootstrap_gcp_artifact_registry(cwd, project, runtime)

    build_context_dir = os.path.join(target_dir, "container-context")
    if os.path.isdir(build_context_dir):
        shutil.rmtree(build_context_dir)
    materialize_gcp_build_context(runtime, handler_path, build_context_dir)

    digest = sha256_tree(build_context_dir)
    image_ref = gcp_image_reference(project, runtime, digest)
    run_checked(
        [
            "gcloud",
            "builds",
            "submit",
            build_context_dir,
            "--project",
            project["gcp"]["project_id"],
            "--tag",
            image_ref,
        ]
    )
    return {
        "cloud": "gcp",
        "runtime": runtime,
        "handler_path": handler_path,
        "validated_template": validation,
        "artifact_path": build_context_dir,
        "artifact_reference": image_ref,
        "sha256": digest,
        "build_context_dir": build_context_dir,
        "image_ref": image_ref,
    }


def bootstrap_gcp_artifact_registry(cwd: str, project: dict[str, Any], runtime: str) -> None:
    target_dir = infra_dir(cwd, "gcp")
    if not os.path.isdir(target_dir):
        raise UserError(
            f"Infrastructure directory does not exist yet: {target_dir}. Run `triage infra generate --cloud gcp --runtime {runtime}` first."
        )
    tfvars_path = os.path.join(target_dir, "terraform.tfvars.json")
    if not os.path.exists(tfvars_path):
        inputs = generate_inputs(project, "gcp", runtime)
        write_file(tfvars_path, json.dumps(inputs, indent=2, sort_keys=True) + "\n")

    run_checked(["terraform", "init", "-input=false", "-no-color"], cwd=target_dir)
    run_checked(
        [
            "terraform",
            "apply",
            "-input=false",
            "-no-color",
            "-auto-approve",
            '-target=google_project_service.required["artifactregistry.googleapis.com"]',
            '-target=google_project_service.required["cloudbuild.googleapis.com"]',
            "-target=google_artifact_registry_repository.handler",
        ],
        cwd=target_dir,
    )


def materialize_gcp_build_context(runtime: str, handler_path: str, build_context_dir: str) -> None:
    copy_tree(handler_path, build_context_dir)
    write_file(os.path.join(build_context_dir, "Dockerfile"), gcp_dockerfile(runtime))
    write_file(
        os.path.join(build_context_dir, ".dockerignore"),
        ".git\n__pycache__\n.pytest_cache\n.venv\nvenv\n.triage\n.env\n.env.*\n!.env.example\n",
    )


def copy_tree(source_dir: str, target_dir: str) -> None:
    for root, dirnames, filenames in os.walk(source_dir):
        dirnames[:] = [name for name in dirnames if not should_skip_build_context_name(name, is_dir=True)]
        root_path = os.path.abspath(root)
        relative = os.path.relpath(root_path, source_dir)
        destination_root = target_dir if relative == "." else os.path.join(target_dir, relative)
        os.makedirs(destination_root, exist_ok=True)
        for filename in filenames:
            if should_skip_build_context_name(filename):
                continue
            source_path = os.path.join(root_path, filename)
            shutil.copy2(source_path, os.path.join(destination_root, filename))


def should_skip_build_context_name(name: str, is_dir: bool = False) -> bool:
    if is_dir and name in {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}:
        return True
    if name in {".DS_Store", ".coverage", ".env"}:
        return True
    if name.startswith(".env.") and name != ".env.example":
        return True
    return name.endswith((".pyc", ".pyo", ".tmp", ".swp"))


def gcp_dockerfile(runtime: str) -> str:
    if runtime == "go":
        return """FROM golang:1.26.1 AS builder
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/triage-handler ./cmd/triage-handler

FROM gcr.io/distroless/base-debian12
ENV PORT=8080
COPY --from=builder /out/triage-handler /triage-handler
EXPOSE 8080
ENTRYPOINT ["/triage-handler"]
"""
    if runtime == "python":
        return """FROM python:3.14.3-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8080
CMD ["python", "app.py"]
"""
    raise UserError(f"Unsupported GCP runtime for container packaging: {runtime}")


def gcp_image_reference(project: dict[str, Any], runtime: str, digest: str) -> str:
    gcp = project["gcp"]
    env_slug = normalize_env_slug(project.get("env", "dev"))
    version_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", VERSION)
    tag = f"{runtime}-{env_slug}-{version_slug}-{digest[:12]}"
    return (
        f"{gcp['region']}-docker.pkg.dev/"
        f"{gcp['project_id']}/{gcp['artifact_registry_repository']}/triage-handler:{tag}"
    )


def gcp_placeholder_image_reference(project: dict[str, Any], runtime: str) -> str:
    gcp = project["gcp"]
    env_slug = normalize_env_slug(project.get("env", "dev"))
    version_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", VERSION)
    tag = f"{runtime}-{env_slug}-{version_slug}-pending"
    return (
        f"{gcp['region']}-docker.pkg.dev/"
        f"{gcp['project_id']}/{gcp['artifact_registry_repository']}/triage-handler:{tag}"
    )


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: str) -> str:
    digest = hashlib.sha256()
    for current_root, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        rel_root = os.path.relpath(current_root, root)
        for filename in filenames:
            path = os.path.join(current_root, filename)
            relative = filename if rel_root == "." else os.path.join(rel_root, filename)
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def terraform_main(cloud: str) -> str:
    if cloud == "gcp":
        return """terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

locals {
  handler_service_account_id = "triage-handler"
  push_service_account_id    = "triage-push-invoker"
  gcp_sinks                  = { for sink in var.sinks : sink.name => sink }
}

resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "handler" {
  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]

  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository
  description   = "OpenIncidents handler images"
  format        = "DOCKER"
}

resource "google_service_account" "handler" {
  depends_on = [google_project_service.required["iam.googleapis.com"]]

  account_id   = local.handler_service_account_id
  display_name = "OpenIncidents triage-handler runtime"
}

resource "google_service_account" "push_invoker" {
  depends_on = [google_project_service.required["iam.googleapis.com"]]

  account_id   = local.push_service_account_id
  display_name = "OpenIncidents Pub/Sub push invoker"
}

resource "google_cloud_run_v2_service" "handler" {
  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_artifact_registry_repository.handler,
  ]

  name               = var.cloud_run_service_name
  location           = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.handler.email

    containers {
      image = var.container_image

      env {
        name  = "TRIAGE_GCP_SINK_ROUTING"
        value = jsonencode([
          for sink in var.sinks : {
            sink_name       = sink.name
            repo_name       = sink.repo_name
            repo_match_like = sink.repo_match_like
          }
        ])
      }

      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "push_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.handler.location
  name     = google_cloud_run_v2_service.handler.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.push_invoker.email}"
}

resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.push_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic" "logs" {
  depends_on = [google_project_service.required["pubsub.googleapis.com"]]

  name = var.topic_name
}

resource "google_logging_project_sink" "logs" {
  depends_on = [google_project_service.required["logging.googleapis.com"]]

  for_each = local.gcp_sinks

  project                = var.project_id
  name                   = each.value.name
  description            = each.value.description
  destination            = "pubsub.googleapis.com/${google_pubsub_topic.logs.id}"
  filter                 = trimspace(each.value.filter) != "" ? each.value.filter : null
  unique_writer_identity = true

  dynamic "exclusions" {
    for_each = each.value.exclusions
    content {
      name        = exclusions.value.name
      description = exclusions.value.description
      filter      = exclusions.value.filter
    }
  }
}

resource "google_pubsub_topic_iam_member" "sink_writer" {
  for_each = local.gcp_sinks

  topic  = google_pubsub_topic.logs.name
  role   = "roles/pubsub.publisher"
  member = google_logging_project_sink.logs[each.key].writer_identity
}

resource "google_pubsub_subscription" "push" {
  depends_on = [
    google_cloud_run_v2_service_iam_member.push_invoker,
    google_service_account_iam_member.pubsub_token_creator,
  ]

  name  = var.subscription_name
  topic = google_pubsub_topic.logs.name

  push_config {
    push_endpoint = google_cloud_run_v2_service.handler.uri

    oidc_token {
      service_account_email = google_service_account.push_invoker.email
    }
  }
}

output "pubsub_topic" {
  value = google_pubsub_topic.logs.name
}

output "pubsub_subscription" {
  value = google_pubsub_subscription.push.name
}

output "sink_writer_identities" {
  value = { for key, sink in google_logging_project_sink.logs : key => sink.writer_identity }
}

output "cloud_run_url" {
  value = google_cloud_run_v2_service.handler.uri
}

output "artifact_registry_repository" {
  value = google_artifact_registry_repository.handler.repository_id
}

output "deployment_summary" {
  value = {
    cloud           = "gcp"
    runtime         = var.runtime
    container_image = var.container_image
    sink_count      = length(var.sinks)
    pubsub_topic    = var.topic_name
    pubsub_subscription = var.subscription_name
    routing_mode    = "shared_topic_shared_subscription"
    sinks = {
      for sink in var.sinks : sink.name => {
        repo_name         = sink.repo_name
        repo_match_like   = sink.repo_match_like
        filter            = sink.filter
        exclusion_names   = [for exclusion in sink.exclusions : exclusion.name]
      }
    }
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
        return """variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "env" {
  type = string
}

variable "topic_name" {
  type = string
}

variable "subscription_name" {
  type = string
}

variable "sinks" {
  type = list(object({
    name              = string
    repo_name         = string
    repo_match_like   = string
    description       = string
    filter            = string
    exclusions = list(object({
      name        = string
      description = string
      filter      = string
    }))
  }))
}

variable "cloud_run_service_name" {
  type = string
}

variable "artifact_registry_repository" {
  type = string
}

variable "container_image" {
  type = string
}

variable "runtime" {
  type = string
}
"""
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
