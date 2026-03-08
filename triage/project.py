"""Project configuration helpers for ``triage.yaml`` and scaffold layout."""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from .constants import (
    DEFAULT_AWS,
    DEFAULT_GCP,
    DEFAULT_INTEGRATIONS,
    DEFAULT_LLM,
    DEFAULT_POLICY,
    KEY_ORDERS,
    TOP_LEVEL_KEY_ORDER,
    VALID_CLOUDS,
    VALID_ROUTINGS,
    VALID_SEVERITIES,
)
from .errors import UserError
from .state import SECRET_SENTINEL, llm_env_name
from .yaml_subset import dump_yaml, load_yaml

PROJECT_FILE = "triage.yaml"

CONFIG_WHERE = {
    "integrations.jira.enabled": {
        "scope": "project",
        "location": PROJECT_FILE,
        "command": "triage config wizard",
        "effect": "Next `triage run` and next deployed runtime after `triage infra apply`.",
    },
    "policy.jira_min_severity": {
        "scope": "project",
        "location": PROJECT_FILE,
        "command": "triage config wizard",
        "effect": "Next `triage run` and next deployed runtime after `triage infra apply`.",
    },
    "integrations.routing": {
        "scope": "project",
        "location": PROJECT_FILE,
        "command": "triage config wizard",
        "effect": "Next `triage run` and next deployed runtime after `triage infra apply`.",
    },
    "llm.provider": {
        "scope": "project+local",
        "location": f"{PROJECT_FILE} and local CLI state",
        "command": "triage config wizard or triage settings set llm.provider <value>",
        "effect": "Project default takes effect on next `triage run`; local bootstrap takes effect on the next CLI invocation.",
    },
    "llm.model": {
        "scope": "project+local",
        "location": f"{PROJECT_FILE} and local CLI state",
        "command": "triage config wizard or triage settings set llm.model <value>",
        "effect": "Project default takes effect on next `triage run`; local bootstrap takes effect on the next CLI invocation.",
    },
    "llm.api_key": {
        "scope": "local",
        "location": "local CLI state",
        "command": "triage settings set llm.api_key <value> or triage config wizard",
        "effect": "Next command that needs bootstrap completion or LLM-backed execution.",
    },
    "default_cloud": {
        "scope": "local",
        "location": "local CLI state",
        "command": "triage settings set default_cloud <value> or triage config wizard",
        "effect": "Next CLI invocation.",
    },
    "gcp.log_filter_override": {
        "scope": "project",
        "location": PROJECT_FILE,
        "command": "triage config wizard",
        "effect": "Next `triage infra generate`, `triage infra plan`, or `triage infra apply`; deployed effect after apply.",
    },
    "aws.filter_pattern_override": {
        "scope": "project",
        "location": PROJECT_FILE,
        "command": "triage config wizard",
        "effect": "Next `triage infra generate`, `triage infra plan`, or `triage infra apply`; deployed effect after apply.",
    },
}


def order_for(path: str, keys) -> list[str]:
    if not path:
        preferred = TOP_LEVEL_KEY_ORDER
    else:
        normalized = path
        if normalized.startswith("repos."):
            normalized = "repo." + normalized[len("repos.") :]
        if normalized == "repos":
            normalized = "repo"
        preferred = KEY_ORDERS.get(normalized, ())
    ordered = [key for key in preferred if key in keys]
    seen = set(ordered)
    for key in keys:
        if key not in seen:
            ordered.append(key)
    return ordered


def project_file_path(cwd: str) -> str:
    return os.path.join(cwd, PROJECT_FILE)


def project_paths(cwd: str) -> dict[str, str]:
    return {
        "project_config": os.path.abspath(project_file_path(cwd)),
        "env_example": os.path.abspath(os.path.join(cwd, ".env.example")),
        "project_triage_dir": os.path.abspath(os.path.join(cwd, ".triage")),
    }


def default_project_config(
    cloud: str = "gcp", llm_provider: str = "none", llm_model: str | None = None
) -> dict[str, Any]:
    llm = copy.deepcopy(DEFAULT_LLM)
    llm["provider"] = llm_provider
    llm["model"] = llm_model or ""
    llm["api_key_env"] = llm_env_name(llm_provider) or ""
    return {
        "cloud": cloud,
        "env": "dev",
        "repos": [],
        "policy": copy.deepcopy(DEFAULT_POLICY),
        "gcp": copy.deepcopy(DEFAULT_GCP),
        "aws": copy.deepcopy(DEFAULT_AWS),
        "llm": llm,
        "integrations": copy.deepcopy(DEFAULT_INTEGRATIONS),
    }


def normalize_project_config(data: dict[str, Any] | None) -> dict[str, Any]:
    config = default_project_config()
    if not data:
        return config
    for key in TOP_LEVEL_KEY_ORDER:
        if key in data:
            config[key] = data[key]
    config.setdefault("repos", [])
    config.setdefault("policy", copy.deepcopy(DEFAULT_POLICY))
    config.setdefault("gcp", copy.deepcopy(DEFAULT_GCP))
    config.setdefault("aws", copy.deepcopy(DEFAULT_AWS))
    config.setdefault("llm", copy.deepcopy(DEFAULT_LLM))
    config.setdefault("integrations", copy.deepcopy(DEFAULT_INTEGRATIONS))
    return config


def load_project_config(cwd: str, optional: bool = False) -> dict[str, Any] | None:
    path = project_file_path(cwd)
    if not os.path.exists(path):
        if optional:
            return None
        raise UserError(f"Project config not found: {os.path.abspath(path)}")
    with open(path, "r", encoding="utf-8") as handle:
        data = load_yaml(handle.read())
    return normalize_project_config(data)


def save_project_config(cwd: str, config: dict[str, Any]) -> None:
    path = project_file_path(cwd)
    write_file(path, render_project_config(config))


def render_project_config(config: dict[str, Any]) -> str:
    normalized = normalize_project_config(config)
    return dump_yaml(normalized, order_resolver=order_for)


def scaffold_files(
    cwd: str, cloud: str = "gcp", llm_provider: str = "none", llm_model: str | None = None
) -> None:
    os.makedirs(os.path.join(cwd, ".triage", "infra"), exist_ok=True)
    os.makedirs(os.path.join(cwd, ".triage", "build"), exist_ok=True)
    os.makedirs(os.path.join(cwd, ".triage", "cache"), exist_ok=True)
    if not os.path.exists(os.path.join(cwd, ".gitignore")):
        write_file(
            os.path.join(cwd, ".gitignore"),
            ".env\n.triage/build/\n",
        )
    if not os.path.exists(os.path.join(cwd, ".env.example")):
        write_file(cwd + "/.env.example", default_env_example())
    if not os.path.exists(project_file_path(cwd)):
        save_project_config(cwd, default_project_config(cloud, llm_provider, llm_model))


def default_env_example() -> str:
    return (
        "OPENAI_API_KEY=\n"
        "ANTHROPIC_API_KEY=\n"
        "SLACK_WEBHOOK_URL=\n"
        "DISCORD_WEBHOOK_URL=\n"
        "JIRA_EMAIL=\n"
        "JIRA_API_TOKEN=\n"
        "GIT_USERNAME=\n"
        "GIT_TOKEN=\n"
    )


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def effective_view(
    project_config: dict[str, Any] | None, local_state: dict[str, Any] | None
) -> dict[str, Any]:
    project = normalize_project_config(project_config)
    effective = annotate(project, "project")
    if local_state:
        effective["default_cloud"] = {
            "value": local_state.get("default_cloud"),
            "source": "local",
        }
        effective["cloud_validation"] = annotate(local_state.get("clouds", {}), "local")
        effective["bootstrap_complete"] = {
            "value": bool(local_state.get("bootstrap_complete")),
            "source": "local",
        }
        effective.setdefault("llm", {})
        effective["llm"]["api_key"] = {
            "value": SECRET_SENTINEL
            if local_state.get("llm", {}).get("api_key_value")
            else None,
            "source": "local",
        }
    else:
        effective["default_cloud"] = {"value": None, "source": "missing"}
        effective["cloud_validation"] = {"value": None, "source": "missing"}
        effective["bootstrap_complete"] = {"value": False, "source": "missing"}
    return effective


def annotate(value: Any, source: str) -> Any:
    if isinstance(value, dict):
        return {key: annotate(child, source) for key, child in value.items()}
    if isinstance(value, list):
        return [annotate(child, source) for child in value]
    return {"value": value, "source": source}


def config_where(key: str, cwd: str, local_state_path: str) -> dict[str, str]:
    if key in CONFIG_WHERE:
        entry = CONFIG_WHERE[key].copy()
    elif key.endswith("_env"):
        entry = {
            "scope": "project",
            "location": PROJECT_FILE,
            "command": "triage config wizard",
            "effect": "Next `triage run` and next deployed runtime after `triage infra apply`.",
        }
    elif key.startswith(("policy.", "integrations.", "gcp.", "aws.", "repos.", "cloud", "env")):
        entry = {
            "scope": "project",
            "location": PROJECT_FILE,
            "command": "triage config wizard",
            "effect": "Next relevant CLI command and next deployed runtime after `triage infra apply`.",
        }
    else:
        raise UserError(f"Unknown config key: {key}")
    location = entry["location"]
    if location == PROJECT_FILE:
        entry["location"] = os.path.abspath(project_file_path(cwd))
    elif location == "local CLI state":
        entry["location"] = os.path.abspath(local_state_path)
    elif location == f"{PROJECT_FILE} and local CLI state":
        entry["location"] = (
            f"{os.path.abspath(project_file_path(cwd))} and "
            f"{os.path.abspath(local_state_path)}"
        )
    entry["key"] = key
    return entry


def validate_project_config(project: dict[str, Any], cloud: str) -> list[str]:
    errors = []
    if project.get("cloud") not in VALID_CLOUDS:
        errors.append("`cloud` must be `gcp` or `aws`.")
    if project.get("integrations", {}).get("routing") not in VALID_ROUTINGS:
        errors.append("`integrations.routing` must be `slack`, `discord`, or `both`.")
    severity = project.get("policy", {}).get("severity_min")
    jira_severity = project.get("policy", {}).get("jira_min_severity")
    if severity not in VALID_SEVERITIES:
        errors.append("`policy.severity_min` has an invalid severity.")
    if jira_severity not in VALID_SEVERITIES:
        errors.append("`policy.jira_min_severity` has an invalid severity.")
    llm = project.get("llm", {})
    if llm.get("provider") not in ("none", "openai", "anthropic"):
        errors.append("`llm.provider` must be `none`, `openai`, or `anthropic`.")
    if llm.get("provider") != "none":
        if not llm.get("model"):
            errors.append("`llm.model` is required when `llm.provider` is not `none`.")
        if not llm.get("api_key_env"):
            errors.append("`llm.api_key_env` is required when `llm.provider` is not `none`.")
    if cloud == "gcp":
        for field in (
            "project_id",
            "region",
            "sink_name",
            "topic_name",
            "subscription_name",
            "cloud_run_service_name",
            "artifact_registry_repository",
        ):
            if not project.get("gcp", {}).get(field):
                errors.append(f"`gcp.{field}` is required.")
    if cloud == "aws":
        aws = project.get("aws", {})
        for field in ("region", "log_group_name", "lambda_name", "package_format", "filter_name", "log_format"):
            if not aws.get(field):
                errors.append(f"`aws.{field}` is required.")
        if aws.get("log_format") == "json" and not aws.get("severity_field"):
            errors.append("`aws.severity_field` is required when `aws.log_format` is `json`.")
        if aws.get("log_format") == "space_delimited" and not aws.get("severity_word_position"):
            errors.append(
                "`aws.severity_word_position` is required when `aws.log_format` is `space_delimited`."
            )
    return errors


def derive_gcp_log_filter(project: dict[str, Any]) -> str:
    override = project.get("gcp", {}).get("log_filter_override")
    if override:
        return override
    severity = project.get("policy", {}).get("severity_min", "ERROR")
    return f"severity>={severity}"


def severities_at_or_above(minimum: str) -> list[str]:
    if minimum not in VALID_SEVERITIES:
        return ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]
    index = VALID_SEVERITIES.index(minimum)
    return list(VALID_SEVERITIES[index:])


def derive_aws_filter_pattern(project: dict[str, Any]) -> str:
    override = project.get("aws", {}).get("filter_pattern_override")
    if override:
        return override
    aws = project.get("aws", {})
    severities = severities_at_or_above(project.get("policy", {}).get("severity_min", "ERROR"))
    log_format = aws.get("log_format", "json")
    if log_format == "json":
        field = aws.get("severity_field", "severity")
        joined = " || ".join(f'$.{field} = "{severity}"' for severity in severities)
        return "{ " + joined + " }"
    if log_format == "space_delimited":
        position = int(aws.get("severity_word_position", 1))
        joined = " || ".join(f"w{position} = {severity}" for severity in severities)
        return "[ " + joined + " ]"
    return ""


def required_runtime_env_vars(project: dict[str, Any]) -> list[str]:
    vars_needed = []
    llm = project.get("llm", {})
    if llm.get("provider") != "none" and llm.get("api_key_env"):
        vars_needed.append(llm["api_key_env"])
    integrations = project.get("integrations", {})
    if integrations.get("slack", {}).get("enabled"):
        vars_needed.append(integrations["slack"]["webhook_env"])
    if integrations.get("discord", {}).get("enabled"):
        vars_needed.append(integrations["discord"]["webhook_env"])
    if integrations.get("jira", {}).get("enabled"):
        vars_needed.extend(
            [
                integrations["jira"]["email_env"],
                integrations["jira"]["token_env"],
            ]
        )
    for repo in project.get("repos", []):
        auth = repo.get("auth", {})
        if auth.get("username_env"):
            vars_needed.append(auth["username_env"])
        if auth.get("token_env"):
            vars_needed.append(auth["token_env"])
    return sorted({name for name in vars_needed if name})


def render_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"
