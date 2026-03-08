"""Shared constants for the ``triage`` CLI."""

VERSION = "0.1.0"
SCHEMA_VERSION = 1

VALID_CLOUDS = ("gcp", "aws")
VALID_RUNTIMES = ("go", "python")
VALID_LLM_PROVIDERS = ("none", "openai", "anthropic")
VALID_ROUTINGS = ("slack", "discord", "both")
VALID_SEVERITIES = (
    "DEBUG",
    "INFO",
    "NOTICE",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "ALERT",
    "EMERGENCY",
)

DEFAULT_POLICY = {
    "severity_min": "ERROR",
    "jira_min_severity": "CRITICAL",
    "window_seconds": 300,
    "dedupe": True,
    "max_llm_tokens": 2000,
    "rate_limit_per_service_per_min": 6,
}

DEFAULT_GCP = {
    "project_id": "my-project",
    "region": "us-central1",
    "sink_name": "triage-prod",
    "topic_name": "triage-prod",
    "subscription_name": "triage-prod-push",
    "cloud_run_service_name": "triage-handler",
    "artifact_registry_repository": "triage",
    "log_filter_override": "",
}

DEFAULT_AWS = {
    "region": "us-east-1",
    "log_group_name": "/aws/lambda/my-service",
    "lambda_name": "triage-handler",
    "package_format": "zip",
    "filter_name": "triage-prod",
    "log_format": "json",
    "severity_field": "severity",
    "severity_word_position": 1,
    "filter_pattern_override": "",
}

DEFAULT_LLM = {
    "provider": "none",
    "model": "",
    "api_key_env": "",
}

DEFAULT_INTEGRATIONS = {
    "routing": "slack",
    "slack": {
        "enabled": True,
        "webhook_env": "SLACK_WEBHOOK_URL",
    },
    "discord": {
        "enabled": False,
        "webhook_env": "DISCORD_WEBHOOK_URL",
    },
    "jira": {
        "enabled": True,
        "base_url": "https://example.atlassian.net",
        "project_key": "ABC",
        "email_env": "JIRA_EMAIL",
        "token_env": "JIRA_API_TOKEN",
    },
}

TOP_LEVEL_KEY_ORDER = (
    "cloud",
    "env",
    "repos",
    "policy",
    "gcp",
    "aws",
    "llm",
    "integrations",
)

KEY_ORDERS = {
    "policy": (
        "severity_min",
        "jira_min_severity",
        "window_seconds",
        "dedupe",
        "max_llm_tokens",
        "rate_limit_per_service_per_min",
    ),
    "repo": ("name", "git_url", "auth", "local_path", "branch"),
    "repo.auth": ("username_env", "token_env"),
    "gcp": (
        "project_id",
        "region",
        "sink_name",
        "topic_name",
        "subscription_name",
        "cloud_run_service_name",
        "artifact_registry_repository",
        "log_filter_override",
    ),
    "aws": (
        "region",
        "log_group_name",
        "lambda_name",
        "package_format",
        "filter_name",
        "log_format",
        "severity_field",
        "severity_word_position",
        "filter_pattern_override",
    ),
    "llm": ("provider", "model", "api_key_env"),
    "integrations": ("routing", "slack", "discord", "jira"),
    "integrations.slack": ("enabled", "webhook_env"),
    "integrations.discord": ("enabled", "webhook_env"),
    "integrations.jira": (
        "enabled",
        "base_url",
        "project_key",
        "email_env",
        "token_env",
    ),
}

PLACEHOLDER_CONTAINER_IMAGE = "pending://triage-handler-image"
PLACEHOLDER_LAMBDA_PACKAGE = "pending://triage-handler-package"
