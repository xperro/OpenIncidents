"""Project configuration helpers for ``triage.yaml`` and scaffold layout."""

from __future__ import annotations

import copy
import json
import os
import re
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
LEGACY_GCP_RESOURCE_DEFAULTS = {
    "sink_name": "triage-prod",
    "topic_name": "triage-prod",
    "subscription_name": "triage-prod-push",
}

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
    cloud: str = "gcp",
    llm_provider: str = "none",
    llm_model: str | None = None,
    env: str = "dev",
) -> dict[str, Any]:
    llm = copy.deepcopy(DEFAULT_LLM)
    llm["provider"] = llm_provider
    llm["model"] = llm_model or ""
    llm["api_key_env"] = llm_env_name(llm_provider) or ""
    config = {
        "cloud": cloud,
        "env": env,
        "repos": [],
        "policy": copy.deepcopy(DEFAULT_POLICY),
        "gcp": copy.deepcopy(DEFAULT_GCP),
        "aws": copy.deepcopy(DEFAULT_AWS),
        "llm": llm,
        "integrations": copy.deepcopy(DEFAULT_INTEGRATIONS),
    }
    apply_gcp_resource_defaults(config)
    return config


def normalize_env_slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "dev"


def derive_gcp_resource_names(env: Any) -> dict[str, str]:
    env_slug = normalize_env_slug(env)
    prefix = f"triage-{env_slug}"
    return {
        "sink_name": prefix,
        "topic_name": prefix,
        "subscription_name": f"{prefix}-push",
    }


def apply_gcp_resource_defaults(config: dict[str, Any], raw_data: dict[str, Any] | None = None) -> None:
    gcp = config.setdefault("gcp", copy.deepcopy(DEFAULT_GCP))
    raw_gcp = (raw_data or {}).get("gcp", {}) if isinstance(raw_data, dict) else {}
    derived = derive_gcp_resource_names(config.get("env") or "dev")
    for key, value in derived.items():
        current = gcp.get(key)
        if key not in raw_gcp or not current or current == LEGACY_GCP_RESOURCE_DEFAULTS[key]:
            gcp[key] = value


def normalize_gcp_sink_resource_name(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "triage-sink"


def normalize_gcp_exclusion_name(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-")
    if not text:
        return "default-exclusion"
    if not text[0].isalnum():
        text = f"x{text}"
    return text[:100]


def escape_gcp_log_filter_regex(value: str) -> str:
    escaped = re.escape(str(value or "").strip())
    return escaped.replace("\\", "\\\\").replace('"', '\\"')


def build_gcp_repo_match_filter(value: str) -> str:
    regex = escape_gcp_log_filter_regex(value)
    if not regex:
        return ""
    pattern = f".*{regex}.*"
    fields = (
        "logName",
        "textPayload",
        "jsonPayload.message",
        "jsonPayload.repo_name",
        "jsonPayload.repository",
        'labels."run.googleapis.com/service_name"',
        "resource.labels.service_name",
        "resource.labels.revision_name",
        "protoPayload.resourceName",
        "protoPayload.authenticationInfo.principalEmail",
    )
    return " OR ".join(f'{field} =~ "{pattern}"' for field in fields)


def join_gcp_filter_clauses(*clauses: str) -> str:
    parts = [str(clause or "").strip() for clause in clauses if str(clause or "").strip()]
    return " AND ".join(f"({part})" for part in parts)


def derive_gcp_sink_filter(project: dict[str, Any], sink: dict[str, Any]) -> str:
    base_filter = str(sink.get("filter") or "").strip()
    include_severity = str(sink.get("include_severity_at_or_above") or "").strip().upper()
    include_repo_like = str(sink.get("include_repo_name_like") or "").strip()
    resolved = join_gcp_filter_clauses(
        base_filter,
        f"severity>={include_severity}" if include_severity else "",
        build_gcp_repo_match_filter(include_repo_like),
    )
    if resolved:
        return resolved
    return derive_gcp_log_filter(project)


def derive_gcp_sink_exclusions(sink: dict[str, Any]) -> list[dict[str, str]]:
    exclusions = []
    exact_severities = sink.get("exclude_severities") or []
    if isinstance(exact_severities, str):
        exact_severities = [exact_severities]
    normalized_exact = [
        str(severity or "").strip().upper()
        for severity in exact_severities
        if str(severity or "").strip()
    ]
    if normalized_exact:
        severity_filter = " OR ".join(f"severity={severity}" for severity in normalized_exact)
        exclusions.append(
            {
                "name": normalize_gcp_exclusion_name(f"{sink.get('name', 'sink')}-severity-match"),
                "description": f"Exclude exact severities: {', '.join(normalized_exact)}.",
                "filter": severity_filter,
            }
        )
    severity = str(sink.get("exclude_severity_at_or_above") or "").strip().upper()
    if severity:
        exclusions.append(
            {
                "name": normalize_gcp_exclusion_name(f"{sink.get('name', 'sink')}-severity"),
                "description": f"Exclude {severity} and higher severity entries.",
                "filter": f"severity>={severity}",
            }
        )
    repo_like = str(sink.get("exclude_repo_name_like") or "").strip()
    repo_filter = build_gcp_repo_match_filter(repo_like)
    if repo_filter:
        exclusions.append(
            {
                "name": normalize_gcp_exclusion_name(f"{sink.get('name', 'sink')}-repo-mismatch"),
                "description": f"Exclude entries that do not mention `{repo_like}`.",
                "filter": f"NOT ({repo_filter})",
            }
        )
    return exclusions


def normalize_project_config(data: dict[str, Any] | None) -> dict[str, Any]:
    env = (data or {}).get("env", "dev")
    config = default_project_config(env=env)
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
    apply_gcp_resource_defaults(config, data)
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
        gcp = project.get("gcp", {})
        for field in (
            "project_id",
            "region",
            "cloud_run_service_name",
            "artifact_registry_repository",
        ):
            if not gcp.get(field):
                errors.append(f"`gcp.{field}` is required.")
        sinks = gcp.get("sinks") or []
        if not isinstance(sinks, list):
            errors.append("`gcp.sinks` must be a list when present.")
        elif sinks:
            names = set()
            for index, sink in enumerate(sinks):
                prefix = f"`gcp.sinks[{index}]`"
                if not isinstance(sink, dict):
                    errors.append(f"{prefix} must be an object.")
                    continue
                for field in ("name", "repo_name"):
                    if not str(sink.get(field) or "").strip():
                        errors.append(f"{prefix}.{field} is required.")
                name = normalize_gcp_sink_resource_name(sink.get("name"))
                if name in names:
                    errors.append(f"{prefix}.name must be unique after normalization.")
                names.add(name)
                include_severity = str(sink.get("include_severity_at_or_above") or "").strip().upper()
                if include_severity and include_severity not in VALID_SEVERITIES:
                    errors.append(
                        f"{prefix}.include_severity_at_or_above has an invalid severity."
                    )
                severity = str(sink.get("exclude_severity_at_or_above") or "").strip().upper()
                if severity and severity not in VALID_SEVERITIES:
                    errors.append(
                        f"{prefix}.exclude_severity_at_or_above has an invalid severity."
                    )
                exact_severities = sink.get("exclude_severities") or []
                if exact_severities and not isinstance(exact_severities, list):
                    errors.append(f"{prefix}.exclude_severities must be a list when present.")
                elif isinstance(exact_severities, list):
                    for severity in exact_severities:
                        normalized = str(severity or "").strip().upper()
                        if normalized and normalized not in VALID_SEVERITIES:
                            errors.append(f"{prefix}.exclude_severities contains an invalid severity.")
        else:
            for field in ("sink_name", "topic_name", "subscription_name"):
                if not gcp.get(field):
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


def derive_gcp_sinks(project: dict[str, Any]) -> list[dict[str, Any]]:
    gcp = project.get("gcp", {})
    configured = gcp.get("sinks") or []
    if configured:
        resolved = []
        for sink in configured:
            name = normalize_gcp_sink_resource_name(sink.get("name"))
            repo_name = str(sink.get("repo_name") or "").strip()
            repo_match_like = (
                str(sink.get("include_repo_name_like") or "").strip()
                or str(sink.get("exclude_repo_name_like") or "").strip()
                or repo_name
            )
            resolved.append(
                {
                    "name": name,
                    "repo_name": repo_name,
                    "repo_match_like": repo_match_like,
                    "description": str(sink.get("description") or "").strip()
                    or f"OpenIncidents export for {name}.",
                    "filter": derive_gcp_sink_filter(project, sink),
                    "exclusions": derive_gcp_sink_exclusions(sink),
                }
            )
        return resolved
    return [
        {
            "name": gcp["sink_name"],
            "repo_name": gcp["cloud_run_service_name"],
            "repo_match_like": gcp["cloud_run_service_name"],
            "description": f"OpenIncidents export for {gcp['cloud_run_service_name']}.",
            "filter": derive_gcp_log_filter(project),
            "exclusions": [],
        }
    ]


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
