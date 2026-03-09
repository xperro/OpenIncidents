"""argparse-based implementation of the ``triage`` CLI."""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from .constants import VALID_CLOUDS, VALID_LLM_PROVIDERS, VALID_ROUTINGS, VALID_RUNTIMES, VERSION
from .errors import UserError
from .infra import generate_infra, package_handler, terraform_apply, terraform_plan
from .llm_prep import prepare_for_llm
from .llm_prep.repo_context import checkout_repo, enrich_prepared_with_repo_context, local_repo
from .llm_request import build_llm_request_payload, run_llm_client
from .llm_request.client import default_model
from .local_run import load_env_file, run_local
from .notifier import VALID_TARGETS, notify_analysis
from .project import (
    config_where,
    effective_view,
    load_project_config,
    project_file_path,
    project_paths,
    render_json,
    save_project_config,
    scaffold_files,
)
from .state import (
    apply_setting,
    load_state,
    new_state,
    redacted_state,
    save_state,
    state_exists,
    state_path,
)
from .templates import download_template
from .validation import run_subprocess, validate_cloud, validate_runtime


HELP_COMMAND_PATH = ("help",)
ALLOWED_WITHOUT_STATE = {
    HELP_COMMAND_PATH,
    ("init",),
    ("llm-prep",),
    ("llm-request",),
    ("llm-client",),
    ("llm-resolve",),
    ("notify",),
    ("scan",),
    ("config", "show"),
    ("config", "where"),
    ("config", "wizard"),
}
ALLOWED_WITH_PARTIAL_BOOTSTRAP = ALLOWED_WITHOUT_STATE | {
    ("settings", "show"),
    ("settings", "set"),
    ("settings", "validate"),
}


@dataclass
class Context:
    cwd: str
    stdin: Any
    stdout: Any
    stderr: Any


class TriageHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Pretty help output for the CLI while staying within ``argparse``."""


class FriendlyArgumentParser(argparse.ArgumentParser):
    """Argument parser that prints actionable error hints."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", TriageHelpFormatter)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"{self.prog}: error: {message}\n"
            f"hint: run `{self.prog} -h` for usage examples.\n",
        )


def format_examples(*commands: str) -> str:
    if not commands:
        return ""
    return "Examples:\n" + "\n".join(f"  {command}" for command in commands)


def build_parser() -> argparse.ArgumentParser:
    parser = FriendlyArgumentParser(
        prog="triage",
        description=(
            "Bootstrap local state, inspect configuration, download official handler templates, "
            "deploy cloud infrastructure, and replay handlers locally."
        ),
        epilog=format_examples(
            "triage init",
            "triage settings show",
            "triage template download --cloud gcp --runtime go --output /abs/path",
            "triage infra apply --cloud gcp --runtime go --handler-path /abs/path",
            "cat sample-event.json | triage run --cloud gcp --runtime go --handler-path /abs/path",
            "triage help infra apply",
        ),
    )
    parser.add_argument("--version", action="version", version=f"triage {VERSION}")
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="command",
        parser_class=FriendlyArgumentParser,
    )
    help_registry: dict[tuple[str, ...], argparse.ArgumentParser] = {(): parser}

    help_parser = subparsers.add_parser(
        "help",
        aliases=["h"],
        help="Show help for the CLI or a nested command.",
        description="Print top-level help or help for a nested command path.",
        epilog=format_examples(
            "triage help",
            "triage help infra",
            "triage help infra apply",
            "triage h run",
        ),
    )
    help_parser.add_argument(
        "topic",
        nargs="*",
        metavar="command",
        help="Optional command path, for example `infra apply`.",
    )
    help_parser.set_defaults(command_path=HELP_COMMAND_PATH, handler=handle_help, help_registry=help_registry)
    help_registry[("help",)] = help_parser
    help_registry[("h",)] = help_parser

    init_parser = subparsers.add_parser(
        "init",
        help="Bootstrap local CLI state and scaffold the project.",
        description="Interactively validate clouds, select an LLM provider, and scaffold the current project.",
        epilog=format_examples(
            "triage init",
        ),
    )
    init_parser.set_defaults(command_path=("init",), handler=handle_init)
    help_registry[("init",)] = init_parser

    settings = subparsers.add_parser(
        "settings",
        help="Inspect or mutate local CLI settings.",
        description="Inspect or update the per-user CLI state stored outside the repository.",
        epilog=format_examples(
            "triage settings show",
            "triage settings set default_cloud aws",
            "triage settings validate --cloud all",
        ),
    )
    settings.set_defaults(
        command_path=HELP_COMMAND_PATH,
        help_path=("settings",),
        handler=handle_group_help,
        parser_ref=settings,
        available_subcommands=("show", "set", "validate"),
        group_name="settings",
    )
    settings_subparsers = settings.add_subparsers(
        dest="settings_command",
        title="commands",
        metavar="command",
        parser_class=FriendlyArgumentParser,
    )
    help_registry[("settings",)] = settings

    settings_show = settings_subparsers.add_parser(
        "show",
        help="Show redacted local CLI state.",
        description="Render the current local CLI state with secrets redacted.",
        epilog=format_examples(
            "triage settings show",
        ),
    )
    settings_show.set_defaults(command_path=("settings", "show"), handler=handle_settings_show)
    help_registry[("settings", "show")] = settings_show

    settings_set = settings_subparsers.add_parser(
        "set",
        help="Set a writable local CLI key.",
        description="Update a writable key in the per-user CLI state file.",
        epilog=format_examples(
            "triage settings set default_cloud gcp",
            "triage settings set jira.issue_type_default Bug",
            "triage settings set llm.api_key sk-***",
        ),
    )
    settings_set.add_argument("key", metavar="KEY", help="Writable state key, for example `default_cloud`.")
    settings_set.add_argument("value", metavar="VALUE", help="New value to persist for the selected key.")
    settings_set.set_defaults(command_path=("settings", "set"), handler=handle_settings_set)
    help_registry[("settings", "set")] = settings_set

    settings_validate = settings_subparsers.add_parser(
        "validate",
        help="Validate local cloud tooling and credentials.",
        description="Re-run live tooling and credential checks for one or more clouds and persist the results.",
        epilog=format_examples(
            "triage settings validate --cloud gcp",
            "triage settings validate --cloud all",
        ),
    )
    settings_validate.add_argument(
        "--cloud",
        choices=("gcp", "aws", "all"),
        required=True,
        help="Cloud to validate right now.",
    )
    settings_validate.set_defaults(command_path=("settings", "validate"), handler=handle_settings_validate)
    help_registry[("settings", "validate")] = settings_validate

    config = subparsers.add_parser(
        "config",
        help="Show config locations and merged state.",
        description="Discover project and local configuration without guessing where values live.",
        epilog=format_examples(
            "triage config show --effective",
            "triage config where llm.api_key",
            "triage config wizard",
        ),
    )
    config.set_defaults(
        command_path=HELP_COMMAND_PATH,
        help_path=("config",),
        handler=handle_group_help,
        parser_ref=config,
        available_subcommands=("show", "where", "wizard"),
        group_name="config",
    )
    config_subparsers = config.add_subparsers(
        dest="config_command",
        title="commands",
        metavar="command",
        parser_class=FriendlyArgumentParser,
    )
    help_registry[("config",)] = config

    config_show = config_subparsers.add_parser(
        "show",
        help="Show project, local, effective, or path views.",
        description="Render project config, local CLI state, merged effective config, or important paths.",
        epilog=format_examples(
            "triage config show --project",
            "triage config show --local",
            "triage config show --effective",
            "triage config show --paths",
        ),
    )
    group = config_show.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", action="store_true", help="Show `./triage.yaml` as written on disk.")
    group.add_argument("--local", action="store_true", help="Show the local CLI state with secrets redacted.")
    group.add_argument("--effective", action="store_true", help="Show the merged effective config view.")
    group.add_argument("--paths", action="store_true", help="Show absolute paths used by the CLI.")
    config_show.set_defaults(command_path=("config", "show"), handler=handle_config_show)
    help_registry[("config", "show")] = config_show

    config_where_parser = config_subparsers.add_parser(
        "where",
        help="Show where a config key lives.",
        description="Explain which file owns a config key, how to edit it, and when the change takes effect.",
        epilog=format_examples(
            "triage config where llm.api_key",
            "triage config where integrations.jira.issue_type",
        ),
    )
    config_where_parser.add_argument("key", metavar="KEY", help="Config key to locate.")
    config_where_parser.set_defaults(command_path=("config", "where"), handler=handle_config_where)
    help_registry[("config", "where")] = config_where_parser

    config_wizard_parser = config_subparsers.add_parser(
        "wizard",
        help="Interactive config workflow.",
        description="Guide common project and local configuration edits interactively.",
        epilog=format_examples(
            "triage config wizard",
        ),
    )
    config_wizard_parser.set_defaults(command_path=("config", "wizard"), handler=handle_config_wizard)
    help_registry[("config", "wizard")] = config_wizard_parser

    template = subparsers.add_parser(
        "template",
        help="Work with bundled handler templates.",
        description="Inspect and extract the official cloud-specific handler templates embedded in the CLI bundle.",
        epilog=format_examples(
            "triage template download --cloud gcp --runtime go --output /abs/path",
            "triage template download --cloud aws --runtime python --output /abs/path --force",
        ),
    )
    template.set_defaults(
        command_path=HELP_COMMAND_PATH,
        help_path=("template",),
        handler=handle_group_help,
        parser_ref=template,
        available_subcommands=("download",),
        group_name="template",
    )
    template_subparsers = template.add_subparsers(
        dest="template_command",
        title="commands",
        metavar="command",
        parser_class=FriendlyArgumentParser,
    )
    help_registry[("template",)] = template
    template_download = template_subparsers.add_parser(
        "download",
        help="Extract a bundled handler template.",
        description="Copy an official handler template to an explicit absolute output directory.",
        epilog=format_examples(
            "triage template download --cloud gcp --runtime go --output /abs/path",
            "triage template download --cloud aws --runtime python --output /abs/path --force",
        ),
    )
    template_download.add_argument("--cloud", choices=VALID_CLOUDS, required=True, help="Cloud variant to extract.")
    template_download.add_argument("--runtime", choices=VALID_RUNTIMES, required=True, help="Handler runtime to extract.")
    template_download.add_argument("--output", required=True, help="Absolute destination directory for the template.")
    template_download.add_argument("--force", action="store_true", help="Overwrite an existing non-empty output directory.")
    template_download.set_defaults(command_path=("template", "download"), handler=handle_template_download)
    help_registry[("template", "download")] = template_download

    infra = subparsers.add_parser(
        "infra",
        help="Generate and run Terraform workflow steps.",
        description="Generate Terraform inputs, plan changes, and apply cloud infrastructure for OpenIncidents.",
        epilog=format_examples(
            "triage infra generate --cloud gcp --runtime go",
            "triage infra plan --cloud gcp --runtime go",
            "triage infra apply --cloud gcp --runtime go --handler-path /abs/path",
        ),
    )
    infra.set_defaults(
        command_path=HELP_COMMAND_PATH,
        help_path=("infra",),
        handler=handle_group_help,
        parser_ref=infra,
        available_subcommands=("generate", "plan", "apply"),
        group_name="infra",
    )
    infra_subparsers = infra.add_subparsers(
        dest="infra_command",
        title="commands",
        metavar="command",
        parser_class=FriendlyArgumentParser,
    )
    help_registry[("infra",)] = infra
    for name, handler in (
        ("generate", handle_infra_generate),
        ("plan", handle_infra_plan),
        ("apply", handle_infra_apply),
    ):
        description = {
            "generate": "Generate Terraform inputs and provider files for the selected cloud and runtime.",
            "plan": "Generate Terraform inputs and produce a Terraform plan for the selected cloud and runtime.",
            "apply": "Build or package the handler, refresh Terraform inputs, and apply the selected cloud stack.",
        }[name]
        examples = {
            "generate": format_examples(
                "triage infra generate --cloud gcp --runtime go",
                "triage infra generate --cloud aws --runtime python",
            ),
            "plan": format_examples(
                "triage infra plan --cloud gcp --runtime go",
                "triage infra plan --cloud aws --runtime python",
            ),
            "apply": format_examples(
                "triage infra apply --cloud gcp --runtime go --handler-path /abs/path",
                "triage infra apply --cloud aws --runtime python --handler-path /abs/path",
            ),
        }[name]
        command = infra_subparsers.add_parser(
            name,
            help=f"Run `triage infra {name}`.",
            description=description,
            epilog=examples,
        )
        command.add_argument(
            "--cloud",
            choices=VALID_CLOUDS,
            help="Cloud to target. Falls back to project or local defaults when omitted.",
        )
        command.add_argument(
            "--runtime",
            choices=VALID_RUNTIMES,
            required=True,
            help="Handler runtime to generate, plan, or deploy.",
        )
        if name == "apply":
            command.add_argument(
                "--handler-path",
                required=True,
                help="Absolute path to the handler template or implementation to deploy.",
            )
        command.set_defaults(command_path=("infra", name), handler=handler)
        help_registry[("infra", name)] = command

    run_parser = subparsers.add_parser(
        "run",
        help="Replay the selected handler locally.",
        description="Run the selected handler locally against a file or piped stdin event payload.",
        epilog=format_examples(
            "triage run --cloud gcp --runtime python --handler-path /abs/path --input /abs/path/sample.json",
            "cat sample-event.json | triage run --cloud gcp --runtime go --handler-path /abs/path",
        ),
    )
    run_parser.add_argument(
        "--cloud",
        choices=VALID_CLOUDS,
        help="Cloud adapter to simulate. Falls back to project or local defaults when omitted.",
    )
    run_parser.add_argument("--runtime", choices=VALID_RUNTIMES, required=True, help="Handler runtime to execute.")
    run_parser.add_argument("--handler-path", required=True, help="Absolute path to the local handler implementation.")
    run_parser.add_argument(
        "--input",
        default="-",
        help="Absolute path to a replay payload, or `-` to read the payload from stdin.",
    )
    run_parser.set_defaults(command_path=("run",), handler=handle_run)
    help_registry[("run",)] = run_parser

    llm_prep_parser = subparsers.add_parser(
        "llm-prep",
        help="Prepare raw cloud events into compact LLM-ready incidents.",
        description=(
            "Decode and normalize mock cloud events, apply severity filtering, dedupe/grouping, "
            "redaction, and context truncation to produce isolated LLM preparation output."
        ),
        epilog=format_examples(
            "triage llm-prep --input /abs/path/events.json --cloud gcp --runtime go",
            "cat events.json | triage llm-prep --cloud aws --runtime python",
        ),
    )
    llm_prep_parser.add_argument(
        "--input",
        default="-",
        help="Absolute path to a JSON payload, or `-` to read from stdin.",
    )
    llm_prep_parser.add_argument(
        "--cloud",
        choices=("auto",) + VALID_CLOUDS,
        default="auto",
        help="Cloud hint used during normalization.",
    )
    llm_prep_parser.add_argument(
        "--runtime",
        choices=("auto",) + VALID_RUNTIMES,
        default="auto",
        help="Runtime hint to include in prepared incidents.",
    )
    llm_prep_parser.add_argument(
        "--severity-min",
        default="ERROR",
        help="Minimum severity to keep after normalization.",
    )
    llm_prep_parser.add_argument(
        "--max-incidents",
        type=int,
        default=20,
        help="Maximum number of grouped incidents in output.",
    )
    llm_prep_parser.add_argument(
        "--max-context-chars",
        type=int,
        default=4000,
        help="Maximum characters for summary/evidence fields.",
    )
    llm_prep_parser.add_argument(
        "--max-stack-lines",
        type=int,
        default=20,
        help="Maximum stacktrace lines to keep.",
    )
    llm_prep_parser.add_argument(
        "--output",
        help="Optional absolute path for JSON output. If omitted, prints to stdout.",
    )
    llm_prep_parser.add_argument(
        "--repo-url",
        action="append",
        default=[],
        help="Optional repository URL to clone and scan for code context. May be repeated.",
    )
    llm_prep_parser.add_argument(
        "--repo-path",
        action="append",
        default=[],
        help="Optional absolute local repository path to scan. May be repeated.",
    )
    llm_prep_parser.add_argument(
        "--repo-branch",
        default="main",
        help="Branch to checkout when using --repo-url.",
    )
    llm_prep_parser.add_argument(
        "--repo-env-var",
        default="TRIAGE_REPO_URLS",
        help=(
            "Environment variable name for repository URLs array. "
            "Accepted format: JSON array or comma/newline-separated URLs."
        ),
    )
    llm_prep_parser.add_argument(
        "--repo-max-files",
        type=int,
        default=3,
        help="Maximum code-context files attached per incident.",
    )
    llm_prep_parser.add_argument(
        "--repo-max-snippet-lines",
        type=int,
        default=80,
        help="Maximum lines per attached code snippet.",
    )
    llm_prep_parser.add_argument(
        "--cost-profile",
        choices=("custom", "lean", "balanced", "deep"),
        default=None,
        help="Optional preset that overrides llm-prep context limits for cost control.",
    )
    llm_prep_parser.add_argument(
        "--cost-profile-env-var",
        default="TRIAGE_LLM_COST_PROFILE",
        help="Environment variable name for default llm-prep cost profile.",
    )
    llm_prep_parser.set_defaults(command_path=("llm-prep",), handler=handle_llm_prep)
    help_registry[("llm-prep",)] = llm_prep_parser

    llm_request_parser = subparsers.add_parser(
        "llm-request",
        help="Build a canonical LLM request payload from llm-prep output.",
        description="Transform prepared incidents into a strict request contract for provider clients.",
        epilog=format_examples(
            "triage llm-request --input /abs/prepared.json --provider mock --model mock-1",
            "triage llm-request --input /abs/prepared.json --provider openai --model gpt-4.1 --output /abs/request.json",
        ),
    )
    llm_request_parser.add_argument("--input", required=True, help="Absolute path to `llm-prep` JSON output.")
    llm_request_parser.add_argument(
        "--provider",
        choices=("openai", "anthropic", "mock"),
        required=True,
        help="Target provider for downstream analysis.",
    )
    llm_request_parser.add_argument("--model", help="Provider model name.")
    llm_request_parser.add_argument(
        "--model-env-var",
        default="TRIAGE_LLM_MODEL",
        help="Environment variable name for default `llm-request` model.",
    )
    llm_request_parser.add_argument("--max-tokens", type=int, default=1200, help="Per-incident token budget.")
    llm_request_parser.add_argument("--output", help="Optional absolute output path for the request payload JSON.")
    llm_request_parser.set_defaults(command_path=("llm-request",), handler=handle_llm_request)
    help_registry[("llm-request",)] = llm_request_parser

    llm_client_parser = subparsers.add_parser(
        "llm-client",
        help="Send LLM request payloads to a provider and collect structured analysis.",
        description="Execute incident analysis against mock/OpenAI/Anthropic using the canonical request payload.",
        epilog=format_examples(
            "triage llm-client --input /abs/request.json --provider mock",
            "triage llm-client --input /abs/request.json --provider openai --api-key-env OPENAI_API_KEY --output /abs/analysis.json",
        ),
    )
    llm_client_parser.add_argument("--input", required=True, help="Absolute path to `llm-request` JSON payload.")
    llm_client_parser.add_argument(
        "--provider",
        choices=("openai", "anthropic", "mock"),
        help="Provider override. Defaults to request payload provider.",
    )
    llm_client_parser.add_argument("--model", help="Model override. Defaults to request payload model.")
    llm_client_parser.add_argument(
        "--api-key-env",
        help="Environment variable name for provider API key. Defaults by provider.",
    )
    llm_client_parser.add_argument("--timeout-seconds", type=int, default=30, help="HTTP timeout for provider calls.")
    llm_client_parser.add_argument("--output", help="Optional absolute output path for analysis JSON.")
    llm_client_parser.set_defaults(command_path=("llm-client",), handler=handle_llm_client)
    help_registry[("llm-client",)] = llm_client_parser

    llm_resolve_parser = subparsers.add_parser(
        "llm-resolve",
        help="Run llm-prep + llm-request + llm-client in one command.",
        description="Execute the full local LLM flow from raw events to final analysis output.",
        epilog=format_examples(
            "cat events.json | triage llm-resolve --cloud gcp --runtime go --provider openai",
            "triage llm-resolve --input /abs/events.json --cloud gcp --runtime go --provider openai --artifact-dir /abs/out",
        ),
    )
    llm_resolve_parser.add_argument("--input", default="-", help="Absolute path to a JSON payload, or `-` for stdin.")
    llm_resolve_parser.add_argument("--output", help="Optional absolute output path for final llm-analysis JSON.")
    llm_resolve_parser.add_argument(
        "--artifact-dir",
        help="Optional absolute directory to persist intermediate files (`prepared.json`, `llm-request.json`, `llm-analysis.json`).",
    )
    llm_resolve_parser.add_argument("--cloud", choices=("auto",) + VALID_CLOUDS, default="auto")
    llm_resolve_parser.add_argument("--runtime", choices=("auto",) + VALID_RUNTIMES, default="auto")
    llm_resolve_parser.add_argument("--severity-min", default="ERROR")
    llm_resolve_parser.add_argument("--max-incidents", type=int, default=20)
    llm_resolve_parser.add_argument("--max-context-chars", type=int, default=4000)
    llm_resolve_parser.add_argument("--max-stack-lines", type=int, default=20)
    llm_resolve_parser.add_argument("--repo-url", action="append", default=[])
    llm_resolve_parser.add_argument("--repo-path", action="append", default=[])
    llm_resolve_parser.add_argument("--repo-branch", default="main")
    llm_resolve_parser.add_argument("--repo-env-var", default="TRIAGE_REPO_URLS")
    llm_resolve_parser.add_argument("--repo-max-files", type=int, default=3)
    llm_resolve_parser.add_argument("--repo-max-snippet-lines", type=int, default=80)
    llm_resolve_parser.add_argument(
        "--cost-profile",
        choices=("custom", "lean", "balanced", "deep"),
        default=None,
    )
    llm_resolve_parser.add_argument("--cost-profile-env-var", default="TRIAGE_LLM_COST_PROFILE")
    llm_resolve_parser.add_argument(
        "--provider",
        choices=("openai", "anthropic", "mock"),
        help="Optional provider override. When omitted, resolves automatically (openai > anthropic > mock).",
    )
    llm_resolve_parser.add_argument("--model")
    llm_resolve_parser.add_argument("--model-env-var", default="TRIAGE_LLM_MODEL")
    llm_resolve_parser.add_argument("--max-tokens", type=int, default=1200)
    llm_resolve_parser.add_argument("--api-key-env")
    llm_resolve_parser.add_argument("--timeout-seconds", type=int, default=30)
    llm_resolve_parser.add_argument("--notify", action="store_true", help="Send notifications after analysis.")
    llm_resolve_parser.add_argument(
        "--notify-target",
        action="append",
        choices=VALID_TARGETS,
        default=[],
        help="Notifier target(s). May be repeated. Defaults to env/config resolution when omitted.",
    )
    llm_resolve_parser.add_argument(
        "--notify-dry-run",
        action="store_true",
        help="Build notifier payloads without sending HTTP requests.",
    )
    llm_resolve_parser.set_defaults(command_path=("llm-resolve",), handler=handle_llm_resolve)
    help_registry[("llm-resolve",)] = llm_resolve_parser

    notify_parser = subparsers.add_parser(
        "notify",
        help="Send llm-analysis results to Slack, Discord, or Jira.",
        description="Dispatch notifications from a llm-analysis JSON payload using env-backed credentials.",
        epilog=format_examples(
            "triage notify --input /abs/llm-analysis.json --target discord",
            "triage notify --input /abs/llm-analysis.json --target slack --target jira --dry-run",
        ),
    )
    notify_parser.add_argument("--input", required=True, help="Absolute path to `llm-analysis` JSON payload.")
    notify_parser.add_argument(
        "--target",
        action="append",
        choices=VALID_TARGETS,
        default=[],
        help="Notifier target(s). May be repeated. Defaults to env/config resolution when omitted.",
    )
    notify_parser.add_argument("--dry-run", action="store_true", help="Build payloads without sending requests.")
    notify_parser.add_argument("--output", help="Optional absolute path for notifier report JSON.")
    notify_parser.set_defaults(command_path=("notify",), handler=handle_notify)
    help_registry[("notify",)] = notify_parser

    scan_parser = subparsers.add_parser(
        "scan",
        help="Run end-to-end scan: ingest logs, analyze with LLM, and notify.",
        description=(
            "Fetch events from GCP Pub/Sub or from input JSON, run llm-prep/request/client, "
            "and optionally notify Slack/Discord/Jira."
        ),
        epilog=format_examples(
            "triage scan --cloud gcp --runtime go --notify --notify-target discord",
            "triage scan --cloud gcp --runtime go --input /abs/events.json --provider openai --notify",
        ),
    )
    scan_parser.add_argument("--cloud", choices=("gcp", "aws"), default="gcp")
    scan_parser.add_argument("--runtime", choices=("auto",) + VALID_RUNTIMES, default="auto")
    scan_parser.add_argument(
        "--input",
        help="Optional absolute input JSON path. If omitted, scan pulls from cloud source.",
    )
    scan_parser.add_argument(
        "--source",
        choices=("gcp-pubsub",),
        default="gcp-pubsub",
        help="Cloud source for event ingestion.",
    )
    scan_parser.add_argument("--subscription", help="GCP Pub/Sub subscription override.")
    scan_parser.add_argument("--project-id", help="GCP project id override.")
    scan_parser.add_argument("--limit", type=int, default=50, help="Max messages to pull from source.")
    scan_parser.add_argument("--init-config", action="store_true", help="Create default triage config when missing.")
    scan_parser.add_argument("--provider", choices=("openai", "anthropic", "mock"))
    scan_parser.add_argument("--model")
    scan_parser.add_argument("--model-env-var", default="TRIAGE_LLM_MODEL")
    scan_parser.add_argument("--max-tokens", type=int, default=1200)
    scan_parser.add_argument("--api-key-env")
    scan_parser.add_argument("--timeout-seconds", type=int, default=30)
    scan_parser.add_argument("--severity-min", default="ERROR")
    scan_parser.add_argument("--max-incidents", type=int, default=20)
    scan_parser.add_argument("--max-context-chars", type=int, default=4000)
    scan_parser.add_argument("--max-stack-lines", type=int, default=20)
    scan_parser.add_argument("--repo-url", action="append", default=[])
    scan_parser.add_argument("--repo-path", action="append", default=[])
    scan_parser.add_argument("--repo-branch", default="main")
    scan_parser.add_argument("--repo-env-var", default="TRIAGE_REPO_URLS")
    scan_parser.add_argument("--repo-max-files", type=int, default=3)
    scan_parser.add_argument("--repo-max-snippet-lines", type=int, default=80)
    scan_parser.add_argument("--cost-profile", choices=("custom", "lean", "balanced", "deep"), default=None)
    scan_parser.add_argument("--cost-profile-env-var", default="TRIAGE_LLM_COST_PROFILE")
    scan_parser.add_argument("--notify", action="store_true")
    scan_parser.add_argument("--notify-target", action="append", choices=VALID_TARGETS, default=[])
    scan_parser.add_argument("--notify-dry-run", action="store_true")
    scan_parser.add_argument(
        "--artifact-dir",
        help="Optional absolute directory for artifacts (`prepared.json`, `llm-request.json`, `llm-analysis.json`).",
    )
    scan_parser.add_argument("--output", help="Optional absolute path for final scan result JSON.")
    scan_parser.set_defaults(command_path=("scan",), handler=handle_scan)
    help_registry[("scan",)] = scan_parser

    return parser


def main(argv: list[str] | None = None, cwd: str | None = None, stdin=None, stdout=None, stderr=None) -> int:
    context = Context(
        cwd=os.path.abspath(cwd or os.getcwd()),
        stdin=stdin or sys.stdin,
        stdout=stdout or sys.stdout,
        stderr=stderr or sys.stderr,
    )
    parser = build_parser()
    try:
        with contextlib.redirect_stdout(context.stdout), contextlib.redirect_stderr(context.stderr):
            args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if not getattr(args, "command", None):
        parser.print_help(context.stdout)
        return 0
    try:
        enforce_bootstrap_gate(getattr(args, "command_path"))
        return int(args.handler(args, context) or 0)
    except UserError as exc:
        context.stderr.write(f"error: {exc}\n")
        return 1
    except KeyboardInterrupt:
        context.stderr.write("Interrupted.\n")
        return 130


def enforce_bootstrap_gate(command_path: tuple[str, ...]) -> None:
    state = load_state(optional=True)
    if state is None:
        if command_path not in ALLOWED_WITHOUT_STATE:
            raise UserError(
                "Local CLI state does not exist yet. Allowed commands before bootstrap: "
                "`help`, `version`, `init`, `config show`, `config where`, and `config wizard`."
            )
        return
    if not state.get("bootstrap_complete") and command_path not in ALLOWED_WITH_PARTIAL_BOOTSTRAP:
        raise UserError(
            "Bootstrap is not complete yet. Finish `triage init` or use `triage settings validate` "
            "and `triage settings set llm.api_key <value>` before running operational commands."
        )


def handle_help(args, context: Context) -> int:
    topic = tuple(args.topic)
    parser = args.help_registry.get(topic)
    if parser is None:
        requested = " ".join(args.topic)
        raise UserError(
            f"Unknown help topic `{requested}`. Run `triage -h` to list the available commands."
        )
    parser.print_help(context.stdout)
    return 0


def handle_group_help(args, context: Context) -> int:
    args.parser_ref.print_help(context.stderr)
    context.stderr.write(
        f"\nerror: choose one `{args.group_name}` command: {', '.join(args.available_subcommands)}\n"
    )
    context.stderr.write(
        f"hint: run `triage help {' '.join(args.help_path)}` or `triage {' '.join(args.help_path)} -h` for details.\n"
    )
    return 2


def prompt(context: Context, label: str, default: str | None = None, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    context.stdout.write(f"{label}{suffix}: ")
    context.stdout.flush()
    answer = context.stdin.readline()
    if answer == "":
        return default or ""
    value = answer.rstrip("\n")
    if not value and default is not None:
        return default
    return value


def prompt_choice(context: Context, label: str, options: tuple[str, ...], default: str | None = None) -> str:
    while True:
        joined = "/".join(options)
        value = prompt(context, f"{label} ({joined})", default=default)
        if value in options:
            return value
        context.stderr.write(f"Invalid choice: {value}\n")


def handle_init(args, context: Context) -> int:
    cloud_selection = prompt_choice(context, "Validate which cloud now", ("gcp", "aws", "both"), default="gcp")
    provider = prompt_choice(
        context,
        "Choose the LLM provider",
        VALID_LLM_PROVIDERS,
        default="none",
    )
    model = ""
    token = ""
    if provider != "none":
        model = prompt(context, "LLM model", default="gpt-4.1" if provider == "openai" else "claude-3-7-sonnet")
        token = prompt(context, f"{provider} API token")

    selected_clouds = list(VALID_CLOUDS) if cloud_selection == "both" else [cloud_selection]
    results = [validate_cloud(cloud) for cloud in selected_clouds]
    state = new_state()
    for result in results:
        state["clouds"][result.cloud]["enabled"] = result.ok
    if provider != "none":
        state["llm"]["provider"] = provider
        state["llm"]["model"] = model
        from .state import llm_env_name

        state["llm"]["api_key_env"] = llm_env_name(provider)
        state["llm"]["api_key_value"] = token
    else:
        state["llm"]["provider"] = "none"
        state["llm"]["model"] = None
        state["llm"]["api_key_env"] = None
        state["llm"]["api_key_value"] = None

    successful = [result.cloud for result in results if result.ok]
    state["default_cloud"] = successful[0] if successful else selected_clouds[0]
    save_state(state)
    scaffold_files(context.cwd, state["default_cloud"], provider, model or None)

    for result in results:
        context.stdout.write(f"[{result.cloud}] {'ok' if result.ok else 'failed'}\n")
        for check in result.checks:
            context.stdout.write(f"  - {check}\n")
    context.stdout.write(f"Local state: {state_path()}\n")
    context.stdout.write(f"Project config: {project_file_path(context.cwd)}\n")

    if not successful:
        raise UserError(
            "No cloud validated successfully during `triage init`. "
            "The local state was created in partial form; fix credentials and re-run `triage settings validate`."
        )
    if provider != "none" and not token:
        raise UserError(
            "The selected LLM provider requires a token. "
            "Set it with `triage settings set llm.api_key <value>`."
        )
    return 0


def handle_settings_show(args, context: Context) -> int:
    state = load_state()
    context.stdout.write(render_json(redacted_state(state)))
    return 0


def handle_settings_set(args, context: Context) -> int:
    state = load_state()
    apply_setting(state, args.key, args.value)
    save_state(state)
    context.stdout.write(render_json(redacted_state(state)))
    return 0


def handle_settings_validate(args, context: Context) -> int:
    state = load_state()
    selected = VALID_CLOUDS if args.cloud == "all" else (args.cloud,)
    ok = True
    for cloud in selected:
        result = validate_cloud(cloud)
        state["clouds"][cloud]["enabled"] = result.ok
        ok = ok and result.ok
        context.stdout.write(f"[{cloud}] {'ok' if result.ok else 'failed'}\n")
        for check in result.checks:
            context.stdout.write(f"  - {check}\n")
    save_state(state)
    return 0 if ok else 1


def handle_config_show(args, context: Context) -> int:
    if args.paths:
        paths = project_paths(context.cwd)
        paths["local_state"] = os.path.abspath(state_path())
        context.stdout.write(render_json(paths))
        return 0
    if args.project:
        path = project_file_path(context.cwd)
        if not os.path.exists(path):
            raise UserError(f"Project config not found: {os.path.abspath(path)}")
        with open(path, "r", encoding="utf-8") as handle:
            context.stdout.write(handle.read())
        return 0
    if args.local:
        local = load_state(optional=True)
        payload = redacted_state(local) if local else {"initialized": False, "path": state_path()}
        context.stdout.write(render_json(payload))
        return 0
    project = load_project_config(context.cwd, optional=True)
    local = load_state(optional=True)
    context.stdout.write(render_json(effective_view(project, local)))
    return 0


def handle_config_where(args, context: Context) -> int:
    info = config_where(args.key, context.cwd, state_path())
    context.stdout.write(render_json(info))
    return 0


def load_or_create_local_state() -> dict[str, Any]:
    state = load_state(optional=True)
    return state if state is not None else new_state()


def load_or_create_project(context: Context) -> dict[str, Any]:
    project = load_project_config(context.cwd, optional=True)
    if project is not None:
        return project
    local = load_state(optional=True)
    cloud = (local or {}).get("default_cloud") or "gcp"
    from .project import default_project_config

    return default_project_config(cloud=cloud)


def handle_config_wizard(args, context: Context) -> int:
    project = load_or_create_project(context)
    local = load_or_create_local_state()
    context.stdout.write(
        "1. Jira\n2. chat routing\n3. LLM\n4. cloud filter overrides\n5. default cloud\n"
    )
    category = prompt(context, "Select a category", default="1")
    if category == "1":
        enabled = prompt_choice(context, "Enable Jira", ("true", "false"), default="true")
        project["integrations"]["jira"]["enabled"] = enabled == "true"
        project["integrations"]["jira"]["base_url"] = prompt(
            context,
            "Jira base URL",
            default=project["integrations"]["jira"]["base_url"],
        )
        project["integrations"]["jira"]["project_key"] = prompt(
            context,
            "Jira project key",
            default=project["integrations"]["jira"]["project_key"],
        )
        project["integrations"]["jira"]["email_env"] = prompt(
            context,
            "Jira email env var",
            default=project["integrations"]["jira"]["email_env"],
        )
        project["integrations"]["jira"]["token_env"] = prompt(
            context,
            "Jira token env var",
            default=project["integrations"]["jira"]["token_env"],
        )
        project["policy"]["jira_min_severity"] = prompt_choice(
            context,
            "Jira minimum severity",
            ("ERROR", "CRITICAL", "ALERT", "EMERGENCY"),
            default=project["policy"]["jira_min_severity"],
        )
        save_project_config(context.cwd, project)
    elif category == "2":
        routing = prompt_choice(context, "Chat routing", VALID_ROUTINGS, default=project["integrations"]["routing"])
        project["integrations"]["routing"] = routing
        project["integrations"]["slack"]["enabled"] = routing in ("slack", "both")
        project["integrations"]["discord"]["enabled"] = routing in ("discord", "both")
        project["integrations"]["slack"]["webhook_env"] = prompt(
            context,
            "Slack webhook env var",
            default=project["integrations"]["slack"]["webhook_env"],
        )
        project["integrations"]["discord"]["webhook_env"] = prompt(
            context,
            "Discord webhook env var",
            default=project["integrations"]["discord"]["webhook_env"],
        )
        save_project_config(context.cwd, project)
    elif category == "3":
        provider = prompt_choice(context, "Project LLM provider", VALID_LLM_PROVIDERS, default=project["llm"]["provider"])
        project["llm"]["provider"] = provider
        local["llm"]["provider"] = provider
        if provider == "none":
            project["llm"]["model"] = ""
            project["llm"]["api_key_env"] = ""
            local["llm"]["model"] = None
            local["llm"]["api_key_env"] = None
        else:
            project["llm"]["model"] = prompt(context, "Project LLM model", default=project["llm"]["model"] or "")
            env_name = prompt(
                context,
                "Project LLM API key env var",
                default=project["llm"]["api_key_env"] or ("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"),
            )
            token = prompt(context, "Local LLM API token (leave blank to keep current)", default="")
            project["llm"]["api_key_env"] = env_name
            local["llm"]["model"] = project["llm"]["model"]
            local["llm"]["api_key_env"] = env_name
            if token:
                local["llm"]["api_key_value"] = token
        save_project_config(context.cwd, project)
        save_state(local)
    elif category == "4":
        project["gcp"]["log_filter_override"] = prompt(
            context,
            "GCP log_filter_override (blank clears)",
            default=project["gcp"].get("log_filter_override", ""),
        )
        project["aws"]["filter_pattern_override"] = prompt(
            context,
            "AWS filter_pattern_override (blank clears)",
            default=project["aws"].get("filter_pattern_override", ""),
        )
        save_project_config(context.cwd, project)
    elif category == "5":
        default_cloud = prompt_choice(
            context,
            "Default cloud",
            VALID_CLOUDS,
            default=local.get("default_cloud") or project.get("cloud") or "gcp",
        )
        local["default_cloud"] = default_cloud
        save_state(local)
    else:
        raise UserError("Unknown wizard category.")
    context.stdout.write("Config wizard completed.\n")
    return 0


def resolve_cloud(args_cloud: str | None, cwd: str) -> str:
    if args_cloud:
        return args_cloud
    project = load_project_config(cwd, optional=True)
    if project and project.get("cloud") in VALID_CLOUDS:
        return project["cloud"]
    local = load_state(optional=True)
    if local and local.get("default_cloud") in VALID_CLOUDS:
        return local["default_cloud"]
    raise UserError("Unable to resolve cloud. Pass `--cloud` or set `default_cloud`.")


def require_live_validation(cloud: str) -> None:
    result = validate_cloud(cloud)
    if not result.ok:
        raise UserError(f"Live validation failed for `{cloud}`:\n" + "\n".join(result.checks))


def require_runtime_validation(runtime: str) -> None:
    ok, message = validate_runtime(runtime)
    if not ok:
        raise UserError(message)


def handle_template_download(args, context: Context) -> int:
    result = download_template(args.cloud, args.runtime, args.output, args.force)
    context.stdout.write(render_json(result))
    return 0


def handle_infra_generate(args, context: Context) -> int:
    cloud = resolve_cloud(args.cloud, context.cwd)
    require_live_validation(cloud)
    project = load_project_config(context.cwd)
    result = generate_infra(context.cwd, project, cloud, args.runtime)
    context.stdout.write(render_json(result))
    return 0


def handle_infra_plan(args, context: Context) -> int:
    cloud = resolve_cloud(args.cloud, context.cwd)
    require_live_validation(cloud)
    project = load_project_config(context.cwd)
    generate_infra(context.cwd, project, cloud, args.runtime)
    result = terraform_plan(context.cwd, cloud, args.runtime)
    context.stdout.write(render_json(result))
    return 0


def handle_infra_apply(args, context: Context) -> int:
    cloud = resolve_cloud(args.cloud, context.cwd)
    require_live_validation(cloud)
    require_runtime_validation(args.runtime)
    project = load_project_config(context.cwd)
    generate_infra(context.cwd, project, cloud, args.runtime)
    artifact = package_handler(context.cwd, cloud, args.runtime, args.handler_path, project)
    from .infra import generate_inputs
    from .project import write_file

    target_dir = os.path.join(context.cwd, ".triage", "infra", cloud)
    inputs = generate_inputs(project, cloud, args.runtime, artifact["artifact_reference"])
    write_file(
        os.path.join(target_dir, "terraform.tfvars.json"),
        render_json(inputs),
    )
    result = terraform_apply(context.cwd, cloud, args.runtime)
    result["artifact"] = artifact
    context.stdout.write(render_json(result))
    return 0


def handle_run(args, context: Context) -> int:
    cloud = resolve_cloud(args.cloud, context.cwd)
    require_live_validation(cloud)
    require_runtime_validation(args.runtime)
    project = load_project_config(context.cwd)
    result = run_local(
        context.cwd,
        project,
        cloud,
        args.runtime,
        args.handler_path,
        args.input,
        context.stdin,
    )
    context.stdout.write(render_json(result))
    return 0


def handle_llm_prep(args, context: Context) -> int:
    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    args.cost_profile = resolve_cost_profile(args, env)
    apply_cost_profile(args)
    if args.input != "-" and not os.path.isabs(args.input):
        raise UserError("`--input` must be absolute when a file path is provided.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    if args.max_incidents <= 0:
        raise UserError("`--max-incidents` must be greater than zero.")
    if args.max_context_chars <= 0:
        raise UserError("`--max-context-chars` must be greater than zero.")
    if args.max_stack_lines <= 0:
        raise UserError("`--max-stack-lines` must be greater than zero.")
    if args.repo_max_files <= 0:
        raise UserError("`--repo-max-files` must be greater than zero.")
    if args.repo_max_snippet_lines <= 0:
        raise UserError("`--repo-max-snippet-lines` must be greater than zero.")
    if not str(args.repo_env_var or "").strip():
        raise UserError("`--repo-env-var` cannot be empty.")
    if not str(args.cost_profile_env_var or "").strip():
        raise UserError("`--cost-profile-env-var` cannot be empty.")

    if args.input == "-":
        payload = context.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as handle:
            payload = handle.read()

    prepared = prepare_for_llm(
        payload,
        cloud=args.cloud,
        runtime_hint=args.runtime,
        severity_min=str(args.severity_min).upper(),
        max_incidents=args.max_incidents,
        max_context_chars=args.max_context_chars,
        max_stack_lines=args.max_stack_lines,
    )
    repo_sources = build_repo_sources_for_llm(args, context, env)
    if repo_sources:
        prepared = enrich_prepared_with_repo_context(
            prepared,
            repo_sources,
            max_files_per_incident=args.repo_max_files,
            max_snippet_lines=args.repo_max_snippet_lines,
        )
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_sources"] = [
            {
                "repo_name": source.repo_name,
                "repo_url": source.repo_url,
                "branch": source.branch,
                "repo_dir": source.repo_dir,
            }
            for source in repo_sources
        ]
        prepared["meta"]["repo_context_enabled"] = True
    else:
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_context_enabled"] = False
    prepared["meta"]["cost_profile"] = args.cost_profile
    rendered = render_json(prepared)

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        context.stdout.write(rendered)

    target_dir = os.path.join(context.cwd, ".triage", "build", "local", "llm-prep")
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, "last-prep.json"), "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return 0


def handle_llm_request(args, context: Context) -> int:
    if not os.path.isabs(args.input):
        raise UserError("`--input` must be an absolute path.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    if args.max_tokens <= 0:
        raise UserError("`--max-tokens` must be greater than zero.")
    if not str(args.model_env_var or "").strip():
        raise UserError("`--model-env-var` cannot be empty.")
    with open(args.input, "r", encoding="utf-8") as handle:
        prepared = json_load_or_user_error(handle.read(), "llm-prep")
    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    language = resolve_language_setting(env)
    model = resolve_request_model(
        provider=args.provider,
        explicit_model=args.model,
        model_env_var=args.model_env_var,
        env=env,
        cwd=context.cwd,
    )

    payload = build_llm_request_payload(
        prepared,
        provider=args.provider,
        model=model,
        language=language,
        max_tokens=args.max_tokens,
    )
    rendered = render_json(payload)
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        context.stdout.write(rendered)
    target_dir = os.path.join(context.cwd, ".triage", "build", "local", "llm-request")
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, "last-request.json"), "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return 0


def handle_llm_client(args, context: Context) -> int:
    if not os.path.isabs(args.input):
        raise UserError("`--input` must be an absolute path.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    if args.timeout_seconds <= 0:
        raise UserError("`--timeout-seconds` must be greater than zero.")

    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    with open(args.input, "r", encoding="utf-8") as handle:
        request_payload = json_load_or_user_error(handle.read(), "llm-request")
    analysis = run_llm_client(
        request_payload,
        provider=args.provider,
        model=args.model,
        api_key_env=args.api_key_env,
        env=env,
        timeout_seconds=args.timeout_seconds,
    )
    rendered = render_json(analysis)
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        context.stdout.write(rendered)
    target_dir = os.path.join(context.cwd, ".triage", "build", "local", "llm-client")
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, "last-analysis.json"), "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return 0


def handle_llm_resolve(args, context: Context) -> int:
    if args.input != "-" and not os.path.isabs(args.input):
        raise UserError("`--input` must be absolute when a file path is provided.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    if args.artifact_dir and not os.path.isabs(args.artifact_dir):
        raise UserError("`--artifact-dir` must be an absolute path.")
    if args.max_tokens <= 0:
        raise UserError("`--max-tokens` must be greater than zero.")
    if args.timeout_seconds <= 0:
        raise UserError("`--timeout-seconds` must be greater than zero.")

    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    provider = resolve_auto_provider(args.provider, env, context.cwd)
    language = resolve_language_setting(env)
    args.cost_profile = resolve_cost_profile(args, env)
    apply_cost_profile(args)

    if args.max_incidents <= 0:
        raise UserError("`--max-incidents` must be greater than zero.")
    if args.max_context_chars <= 0:
        raise UserError("`--max-context-chars` must be greater than zero.")
    if args.max_stack_lines <= 0:
        raise UserError("`--max-stack-lines` must be greater than zero.")
    if args.repo_max_files <= 0:
        raise UserError("`--repo-max-files` must be greater than zero.")
    if args.repo_max_snippet_lines <= 0:
        raise UserError("`--repo-max-snippet-lines` must be greater than zero.")
    if not str(args.repo_env_var or "").strip():
        raise UserError("`--repo-env-var` cannot be empty.")
    if not str(args.cost_profile_env_var or "").strip():
        raise UserError("`--cost-profile-env-var` cannot be empty.")
    if not str(args.model_env_var or "").strip():
        raise UserError("`--model-env-var` cannot be empty.")

    if args.input == "-":
        payload = context.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as handle:
            payload = handle.read()

    prepared = prepare_for_llm(
        payload,
        cloud=args.cloud,
        runtime_hint=args.runtime,
        severity_min=str(args.severity_min).upper(),
        max_incidents=args.max_incidents,
        max_context_chars=args.max_context_chars,
        max_stack_lines=args.max_stack_lines,
    )
    repo_sources = build_repo_sources_for_llm(args, context, env)
    if repo_sources:
        prepared = enrich_prepared_with_repo_context(
            prepared,
            repo_sources,
            max_files_per_incident=args.repo_max_files,
            max_snippet_lines=args.repo_max_snippet_lines,
        )
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_sources"] = [
            {
                "repo_name": source.repo_name,
                "repo_url": source.repo_url,
                "branch": source.branch,
                "repo_dir": source.repo_dir,
            }
            for source in repo_sources
        ]
        prepared["meta"]["repo_context_enabled"] = True
    else:
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_context_enabled"] = False
    prepared["meta"]["cost_profile"] = args.cost_profile

    model = resolve_request_model(
        provider=provider,
        explicit_model=args.model,
        model_env_var=args.model_env_var,
        env=env,
        cwd=context.cwd,
    )
    request_payload = build_llm_request_payload(
        prepared,
        provider=provider,
        model=model,
        language=language,
        max_tokens=args.max_tokens,
    )
    analysis = run_llm_client(
        request_payload,
        provider=provider,
        model=model,
        api_key_env=args.api_key_env,
        env=env,
        timeout_seconds=args.timeout_seconds,
    )

    project = load_project_config(context.cwd, optional=True)
    notify_report = None
    if args.notify:
        targets = resolve_notify_targets(args.notify_target, env, project)
        notify_report = notify_analysis(
            analysis,
            targets=targets,
            env=env,
            project=project,
            dry_run=bool(args.notify_dry_run),
        )

    artifact_dir = args.artifact_dir or os.path.join(context.cwd, ".triage", "build", "local", "llm-resolve")
    os.makedirs(artifact_dir, exist_ok=True)
    prepared_rendered = render_json(prepared)
    request_rendered = render_json(request_payload)
    analysis_rendered = render_json(analysis)
    with open(os.path.join(artifact_dir, "prepared.json"), "w", encoding="utf-8") as handle:
        handle.write(prepared_rendered)
    with open(os.path.join(artifact_dir, "llm-request.json"), "w", encoding="utf-8") as handle:
        handle.write(request_rendered)
    with open(os.path.join(artifact_dir, "llm-analysis.json"), "w", encoding="utf-8") as handle:
        handle.write(analysis_rendered)
    if notify_report is not None:
        with open(os.path.join(artifact_dir, "llm-notify.json"), "w", encoding="utf-8") as handle:
            handle.write(render_json(notify_report))

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(analysis_rendered)
    else:
        context.stdout.write(analysis_rendered)
    return 0


def handle_notify(args, context: Context) -> int:
    if not os.path.isabs(args.input):
        raise UserError("`--input` must be an absolute path.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    with open(args.input, "r", encoding="utf-8") as handle:
        analysis_payload = json_load_or_user_error(handle.read(), "llm-analysis")
    project = load_project_config(context.cwd, optional=True)
    targets = resolve_notify_targets(args.target, env, project)
    report = notify_analysis(
        analysis_payload,
        targets=targets,
        env=env,
        project=project,
        dry_run=bool(args.dry_run),
    )
    rendered = render_json(report)
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        context.stdout.write(rendered)
    target_dir = os.path.join(context.cwd, ".triage", "build", "local", "notify")
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, "last-notify.json"), "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return 0


def handle_scan(args, context: Context) -> int:
    env = load_env_file(os.path.join(context.cwd, ".env"), dict(os.environ))
    apply_scan_env_defaults(args, env)
    if args.input and not os.path.isabs(args.input):
        raise UserError("`--input` must be an absolute path when provided.")
    if args.output and not os.path.isabs(args.output):
        raise UserError("`--output` must be an absolute path.")
    if args.artifact_dir and not os.path.isabs(args.artifact_dir):
        raise UserError("`--artifact-dir` must be an absolute path.")
    if args.limit <= 0:
        raise UserError("`--limit` must be greater than zero.")

    ensure_scan_project_config(context.cwd, init_config=args.init_config)
    project = load_project_config(context.cwd, optional=True)
    if args.cloud != "gcp":
        raise UserError("`triage scan` currently supports only `--cloud gcp`.")

    args.cost_profile = resolve_cost_profile(args, env)
    apply_cost_profile(args)
    language = resolve_language_setting(env)
    provider = resolve_auto_provider(args.provider, env, context.cwd)

    raw_payload = ""
    pulled_count = 0
    if args.input:
        with open(args.input, "r", encoding="utf-8") as handle:
            raw_payload = handle.read()
    else:
        project_id = args.project_id or ((project or {}).get("gcp") or {}).get("project_id")
        subscription = args.subscription or ((project or {}).get("gcp") or {}).get("subscription_name")
        if not project_id or not subscription:
            raise UserError("Missing GCP `project_id` or `subscription_name` for scan source.")
        envelopes, pulled_count = fetch_gcp_pubsub_envelopes(
            context.cwd,
            project_id=str(project_id),
            subscription=str(subscription),
            limit=args.limit,
            env=env,
        )
        raw_payload = json.dumps(envelopes)

    prepared = prepare_for_llm(
        raw_payload,
        cloud=args.cloud,
        runtime_hint=args.runtime,
        severity_min=str(args.severity_min).upper(),
        max_incidents=args.max_incidents,
        max_context_chars=args.max_context_chars,
        max_stack_lines=args.max_stack_lines,
    )
    repo_sources = build_repo_sources_for_llm(args, context, env)
    if repo_sources:
        prepared = enrich_prepared_with_repo_context(
            prepared,
            repo_sources,
            max_files_per_incident=args.repo_max_files,
            max_snippet_lines=args.repo_max_snippet_lines,
        )
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_sources"] = [
            {
                "repo_name": source.repo_name,
                "repo_url": source.repo_url,
                "branch": source.branch,
                "repo_dir": source.repo_dir,
            }
            for source in repo_sources
        ]
        prepared["meta"]["repo_context_enabled"] = True
    else:
        prepared.setdefault("meta", {})
        prepared["meta"]["repo_context_enabled"] = False
    prepared["meta"]["cost_profile"] = args.cost_profile

    model = resolve_request_model(
        provider=provider,
        explicit_model=args.model,
        model_env_var=args.model_env_var,
        env=env,
        cwd=context.cwd,
    )
    request_payload = build_llm_request_payload(
        prepared,
        provider=provider,
        model=model,
        language=language,
        max_tokens=args.max_tokens,
    )
    analysis = run_llm_client(
        request_payload,
        provider=provider,
        model=model,
        api_key_env=args.api_key_env,
        env=env,
        timeout_seconds=args.timeout_seconds,
    )

    notify_report = None
    if args.notify:
        targets = resolve_notify_targets(args.notify_target, env, project)
        notify_report = notify_analysis(
            analysis,
            targets=targets,
            env=env,
            project=project,
            dry_run=bool(args.notify_dry_run),
        )

    artifact_dir = args.artifact_dir or os.path.join(context.cwd, ".triage", "build", "local", "scan")
    os.makedirs(artifact_dir, exist_ok=True)
    prepared_rendered = render_json(prepared)
    request_rendered = render_json(request_payload)
    analysis_rendered = render_json(analysis)
    with open(os.path.join(artifact_dir, "prepared.json"), "w", encoding="utf-8") as handle:
        handle.write(prepared_rendered)
    with open(os.path.join(artifact_dir, "llm-request.json"), "w", encoding="utf-8") as handle:
        handle.write(request_rendered)
    with open(os.path.join(artifact_dir, "llm-analysis.json"), "w", encoding="utf-8") as handle:
        handle.write(analysis_rendered)
    if notify_report is not None:
        with open(os.path.join(artifact_dir, "llm-notify.json"), "w", encoding="utf-8") as handle:
            handle.write(render_json(notify_report))

    result = {
        "schema_version": "scan-result.v1",
        "cloud": args.cloud,
        "provider": provider,
        "model": model,
        "language": language,
        "source": args.source,
        "meta": {
            "pulled_messages": pulled_count,
            "prepared_incidents": (prepared.get("meta") or {}).get("prepared_incidents", 0),
            "analyzed_incidents": (analysis.get("meta") or {}).get("analyzed_incidents", 0),
            "notified": bool(notify_report),
        },
        "artifacts": {
            "artifact_dir": artifact_dir,
            "prepared": os.path.join(artifact_dir, "prepared.json"),
            "request": os.path.join(artifact_dir, "llm-request.json"),
            "analysis": os.path.join(artifact_dir, "llm-analysis.json"),
            "notify": os.path.join(artifact_dir, "llm-notify.json") if notify_report is not None else "",
        },
    }
    rendered = render_json(result)
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        context.stdout.write(rendered)
    return 0


def json_load_or_user_error(raw_payload: str, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise UserError(f"Input for `{label}` must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise UserError(f"Input for `{label}` must be a JSON object.")
    return payload


def parse_repo_urls_from_env(raw_value: str) -> list[str]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Be permissive with malformed list-like values from CI/host envs.
            text = raw.strip().strip("[]")
            chunks = [piece.strip().strip("'\"") for piece in text.replace("\n", ",").split(",")]
            return [item for item in chunks if item]
        if not isinstance(parsed, list):
            text = raw.strip().strip("[]")
            chunks = [piece.strip().strip("'\"") for piece in text.replace("\n", ",").split(",")]
            return [item for item in chunks if item]
        return [str(item).strip() for item in parsed if str(item).strip()]
    chunks = [piece.strip() for piece in raw.replace("\n", ",").split(",")]
    return [item for item in chunks if item]


def build_repo_sources_for_llm(args, context: Context, env: dict[str, str]) -> list[Any]:
    repo_sources = []
    for path in args.repo_path:
        repo_sources.append(local_repo(path))

    repo_urls = list(args.repo_url)
    repo_urls.extend(parse_repo_urls_from_env(env.get(args.repo_env_var, "")))
    repo_urls.extend(project_repo_urls(context.cwd))
    repo_specs = dedupe_repo_specs(repo_urls, branch=args.repo_branch)

    for spec in repo_specs:
        clone_url = apply_repo_auth(spec["repo_url"], spec.get("auth"), env)
        repo_sources.append(
            checkout_repo(
                context.cwd,
                spec["repo_url"],
                branch=spec["branch"],
                clone_url=clone_url,
            )
        )
    return repo_sources


def apply_cost_profile(args) -> None:
    if not args.cost_profile or args.cost_profile == "custom":
        return
    presets = {
        "lean": {
            "max_incidents": 5,
            "max_context_chars": 1200,
            "max_stack_lines": 8,
            "repo_max_files": 1,
            "repo_max_snippet_lines": 30,
        },
        "balanced": {
            "max_incidents": 10,
            "max_context_chars": 2200,
            "max_stack_lines": 12,
            "repo_max_files": 2,
            "repo_max_snippet_lines": 50,
        },
        "deep": {
            "max_incidents": 20,
            "max_context_chars": 4000,
            "max_stack_lines": 20,
            "repo_max_files": 3,
            "repo_max_snippet_lines": 80,
        },
    }
    selected = presets.get(args.cost_profile)
    if not selected:
        return
    for key, value in selected.items():
        setattr(args, key, value)


def resolve_cost_profile(args, env: dict[str, str]) -> str:
    explicit = str(args.cost_profile or "").strip().lower()
    if explicit:
        return validate_cost_profile(explicit, source="--cost-profile")
    env_var_name = str(args.cost_profile_env_var or "").strip()
    raw = str(env.get(env_var_name, "")).strip() if env_var_name else ""
    if raw:
        return validate_cost_profile(raw.lower(), source=env_var_name)
    return "custom"


def validate_cost_profile(value: str, *, source: str) -> str:
    allowed = {"custom", "lean", "balanced", "deep"}
    if value not in allowed:
        raise UserError(
            f"Invalid cost profile `{value}` from `{source}`. Expected one of: custom, lean, balanced, deep."
        )
    return value


def resolve_auto_provider(explicit_provider: str | None, env: dict[str, str], cwd: str) -> str:
    if explicit_provider:
        return explicit_provider
    openai_key = str(env.get("OPENAI_API_KEY", "")).strip()
    anthropic_key = str(env.get("ANTHROPIC_API_KEY", "")).strip()
    if openai_key:
        return "openai"
    if anthropic_key:
        return "anthropic"
    project = load_project_config(cwd, optional=True)
    if project:
        configured = str((project.get("llm") or {}).get("provider") or "").strip()
        if configured in ("openai", "anthropic", "mock"):
            return configured
    return "mock"


def resolve_notify_targets(
    explicit_targets: list[str],
    env: dict[str, str],
    project: dict[str, Any] | None,
) -> list[str]:
    picked = [item for item in explicit_targets if item in VALID_TARGETS]
    if picked:
        return dedupe_strings(picked)
    env_targets = parse_repo_urls_from_env(str(env.get("TRIAGE_NOTIFIER_TARGETS", "")).strip())
    env_picked = [item.lower() for item in env_targets if item.lower() in VALID_TARGETS]
    if env_picked:
        return dedupe_strings(env_picked)
    if isinstance(project, dict):
        integrations = project.get("integrations") if isinstance(project.get("integrations"), dict) else {}
        routing = str((integrations or {}).get("routing") or "").strip().lower()
        derived: list[str] = []
        if routing == "both":
            derived.extend(["slack", "discord"])
        elif routing in ("slack", "discord"):
            derived.append(routing)
        jira_cfg = (integrations or {}).get("jira") if isinstance((integrations or {}).get("jira"), dict) else {}
        if bool(jira_cfg.get("enabled")):
            derived.append("jira")
        if derived:
            return dedupe_strings(derived)
    fallback = []
    if str(env.get("DISCORD_WEBHOOK_URL", "")).strip():
        fallback.append("discord")
    if str(env.get("SLACK_WEBHOOK_URL", "")).strip():
        fallback.append("slack")
    if (
        str(env.get("JIRA_BASE_URL", "")).strip()
        and str(env.get("JIRA_PROJECT_KEY", "")).strip()
        and str(env.get("JIRA_EMAIL", "")).strip()
        and str(env.get("JIRA_API_TOKEN", "")).strip()
    ):
        fallback.append("jira")
    if fallback:
        return dedupe_strings(fallback)
    raise UserError(
        "No notifier targets resolved. Pass `--target`, set `TRIAGE_NOTIFIER_TARGETS`, "
        "or configure webhook/Jira env vars."
    )


def dedupe_strings(values: list[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def apply_scan_env_defaults(args, env: dict[str, str]) -> None:
    if not args.input:
        env_input = str(env.get("TRIAGE_SCAN_INPUT", "")).strip()
        if env_input:
            args.input = env_input
    if not args.project_id:
        env_project = str(env.get("TRIAGE_SCAN_PROJECT_ID", "")).strip()
        if env_project:
            args.project_id = env_project
    if not args.subscription:
        env_subscription = str(env.get("TRIAGE_SCAN_SUBSCRIPTION", "")).strip()
        if env_subscription:
            args.subscription = env_subscription
    if not args.provider:
        env_provider = str(env.get("TRIAGE_SCAN_PROVIDER", "")).strip().lower()
        if env_provider in ("openai", "anthropic", "mock"):
            args.provider = env_provider
    if not args.model:
        env_model = str(env.get("TRIAGE_SCAN_MODEL", "")).strip()
        if env_model:
            args.model = env_model
    if not args.notify and env_bool_true(str(env.get("TRIAGE_SCAN_NOTIFY", "")).strip()):
        args.notify = True
    if not args.notify_target:
        env_targets = parse_repo_urls_from_env(str(env.get("TRIAGE_SCAN_NOTIFY_TARGETS", "")).strip())
        picked = [item.lower() for item in env_targets if item.lower() in VALID_TARGETS]
        if picked:
            args.notify_target = dedupe_strings(picked)
    if args.repo_branch == "main":
        env_branch = str(env.get("TRIAGE_SCAN_REPO_BRANCH", "")).strip()
        if env_branch:
            args.repo_branch = env_branch
    if args.runtime == "auto":
        env_runtime = str(env.get("TRIAGE_SCAN_RUNTIME", "")).strip().lower()
        if env_runtime in ("auto", "go", "python"):
            args.runtime = env_runtime
    if args.cloud == "gcp":
        env_cloud = str(env.get("TRIAGE_SCAN_CLOUD", "")).strip().lower()
        if env_cloud in ("gcp", "aws"):
            args.cloud = env_cloud


def env_bool_true(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def ensure_scan_project_config(cwd: str, *, init_config: bool) -> None:
    path = project_file_path(cwd)
    if os.path.exists(path):
        return
    if not init_config:
        return
    save_project_config(cwd, default_scan_project_config())


def default_scan_project_config() -> dict[str, Any]:
    return {
        "cloud": "gcp",
        "env": "dev",
        "repos": [],
        "policy": {
            "severity_min": "INFO",
            "jira_min_severity": "CRITICAL",
            "window_seconds": 300,
            "dedupe": True,
            "max_llm_tokens": 2000,
            "rate_limit_per_service_per_min": 6,
        },
        "gcp": {
            "project_id": "gcp-course-2024",
            "region": "southamerica-west1",
            "sink_name": "triage-dev",
            "topic_name": "triage-dev",
            "subscription_name": "triage-dev-push",
            "cloud_run_service_name": "triage-handler",
            "artifact_registry_repository": "triage",
            "log_filter_override": "",
            "sinks": [
                {
                    "name": "approve-mrs-dev",
                    "repo_name": "approve-mrs-dev",
                    "description": "Export Cloud Run approval workflow logs for approve-mrs.",
                    "filter": 'resource.type="cloud_run_revision"',
                    "include_severity_at_or_above": "INFO",
                    "include_repo_name_like": "approve-mrs",
                    "exclude_severities": ["DEBUG"],
                },
                {
                    "name": "request-approvals-dev",
                    "repo_name": "request-approvals-dev",
                    "description": "Export Cloud Run deployment and audit logs for request-approvals.",
                    "filter": 'resource.type="cloud_run_revision" OR logName="projects/gcp-course-2024/logs/cloudaudit.googleapis.com%2Fsystem_event"',
                    "include_severity_at_or_above": "INFO",
                    "include_repo_name_like": "request-approvals",
                    "exclude_severities": ["DEBUG"],
                },
            ],
        },
        "aws": {
            "region": "us-east-1",
            "log_group_name": "/aws/lambda/my-service",
            "lambda_name": "triage-handler",
            "package_format": "zip",
            "filter_name": "triage-prod",
            "log_format": "json",
            "severity_field": "severity",
            "severity_word_position": 1,
            "filter_pattern_override": "",
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key_env": "OPENAI_API_KEY",
        },
        "integrations": {
            "routing": "slack",
            "slack": {"enabled": False, "webhook_env": "SLACK_WEBHOOK_URL"},
            "discord": {"enabled": False, "webhook_env": "DISCORD_WEBHOOK_URL"},
            "jira": {
                "enabled": False,
                "base_url": "https://example.atlassian.net",
                "project_key": "ABC",
                "email_env": "JIRA_EMAIL",
                "token_env": "JIRA_API_TOKEN",
            },
        },
    }


def fetch_gcp_pubsub_envelopes(
    cwd: str,
    *,
    project_id: str,
    subscription: str,
    limit: int,
    env: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    command = [
        "gcloud",
        "pubsub",
        "subscriptions",
        "pull",
        subscription,
        "--project",
        project_id,
        "--limit",
        str(limit),
        "--auto-ack",
        "--format=json",
    ]
    result = run_subprocess(command, cwd=cwd, env=env)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise UserError(f"Failed to pull from Pub/Sub subscription `{subscription}`: {detail}")
    raw = result.stdout.strip() or "[]"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserError(f"Unexpected Pub/Sub pull output: {exc}") from exc
    if not isinstance(payload, list):
        raise UserError("Unexpected Pub/Sub pull output: expected a JSON list.")

    envelopes: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        message = item.get("message")
        if not isinstance(message, dict):
            continue
        data = str(message.get("data") or "").strip()
        if not data:
            continue
        normalized_data = ensure_base64_data(data)
        envelopes.append({"message": {"data": normalized_data}})
    return envelopes, len(envelopes)


def ensure_base64_data(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return raw
    # If already valid base64, keep it.
    try:
        base64.b64decode(raw, validate=True)
        return raw
    except Exception:
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def resolve_language_setting(env: dict[str, str]) -> str:
    raw = str(env.get("TRIAGE_LANGUAGE", "")).strip().lower()
    if not raw:
        return "english"
    if raw not in ("english", "spanish"):
        raise UserError("Invalid TRIAGE_LANGUAGE. Expected `english` or `spanish`.")
    return raw


def resolve_request_model(
    *,
    provider: str,
    explicit_model: str | None,
    model_env_var: str,
    env: dict[str, str],
    cwd: str,
) -> str:
    model = str(explicit_model or "").strip()
    if model:
        return model
    provider_env_map = {
        "openai": "TRIAGE_OPENAI_MODEL",
        "anthropic": "TRIAGE_ANTHROPIC_MODEL",
    }
    provider_env_var = provider_env_map.get(provider, "")
    provider_env_model = str(env.get(provider_env_var, "")).strip() if provider_env_var else ""
    if provider_env_model:
        return provider_env_model
    env_model = str(env.get(model_env_var, "")).strip()
    if env_model:
        return env_model
    project = load_project_config(cwd, optional=True)
    if project:
        project_provider = str((project.get("llm") or {}).get("provider") or "").strip()
        project_model = str((project.get("llm") or {}).get("model") or "").strip()
        if project_model and project_provider == provider:
            return project_model
    return default_model(provider)


def project_repo_urls(cwd: str) -> list[dict[str, Any]]:
    project = load_project_config(cwd, optional=True)
    if not project:
        return []
    repos = project.get("repos")
    if not isinstance(repos, list):
        return []
    selected: list[dict[str, Any]] = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        git_url = str(repo.get("git_url") or "").strip()
        if not git_url:
            continue
        selected.append(
            {
                "repo_url": git_url,
                "branch": str(repo.get("branch") or "main").strip() or "main",
                "auth": repo.get("auth") if isinstance(repo.get("auth"), dict) else {},
            }
        )
    return selected


def dedupe_repo_specs(
    repo_inputs: list[str] | list[dict[str, Any]],
    *,
    branch: str,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for item in repo_inputs:
        if isinstance(item, dict):
            repo_url = str(item.get("repo_url") or "").strip()
            repo_branch = str(item.get("branch") or branch).strip() or branch
            auth = item.get("auth") if isinstance(item.get("auth"), dict) else {}
        else:
            repo_url = str(item or "").strip()
            repo_branch = branch
            auth = {}
        if not repo_url:
            continue
        specs.append({"repo_url": repo_url, "branch": repo_branch, "auth": auth})
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        key = (spec["repo_url"], spec["branch"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(spec)
    return unique


def apply_repo_auth(repo_url: str, auth: dict[str, Any], env: dict[str, str]) -> str:
    if not auth:
        return repo_url
    username_env = str(auth.get("username_env") or "").strip()
    token_env = str(auth.get("token_env") or "").strip()
    if not username_env and not token_env:
        return repo_url
    username = env.get(username_env, "").strip() if username_env else ""
    token = env.get(token_env, "").strip() if token_env else ""
    if not username or not token:
        missing = []
        if username_env and not username:
            missing.append(username_env)
        if token_env and not token:
            missing.append(token_env)
        raise UserError(
            "Missing repository credentials from environment: " + ", ".join(missing)
        )
    return inject_basic_auth(repo_url, username, token)


def inject_basic_auth(repo_url: str, username: str, token: str) -> str:
    parsed = urlsplit(repo_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return repo_url
    safe_user = quote(username, safe="")
    safe_token = quote(token, safe="")
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    netloc = f"{safe_user}:{safe_token}@{host}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
