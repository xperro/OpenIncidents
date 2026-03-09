"""argparse-based implementation of the ``triage`` CLI."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any

from .constants import VALID_CLOUDS, VALID_LLM_PROVIDERS, VALID_ROUTINGS, VALID_RUNTIMES, VERSION
from .errors import UserError
from .infra import generate_infra, package_handler, terraform_apply, terraform_plan
from .local_run import run_local
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
from .validation import validate_cloud, validate_runtime


ALLOWED_WITHOUT_STATE = {
    ("init",),
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triage")
    parser.add_argument("--version", action="version", version=f"triage {VERSION}")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Bootstrap local CLI state and scaffold the project.")
    init_parser.set_defaults(command_path=("init",), handler=handle_init)

    settings = subparsers.add_parser("settings", help="Inspect or mutate local CLI settings.")
    settings_subparsers = settings.add_subparsers(dest="settings_command", required=True)

    settings_show = settings_subparsers.add_parser("show", help="Show redacted local CLI state.")
    settings_show.set_defaults(command_path=("settings", "show"), handler=handle_settings_show)

    settings_set = settings_subparsers.add_parser("set", help="Set a writable local CLI key.")
    settings_set.add_argument("key")
    settings_set.add_argument("value")
    settings_set.set_defaults(command_path=("settings", "set"), handler=handle_settings_set)

    settings_validate = settings_subparsers.add_parser("validate", help="Validate local cloud tooling and credentials.")
    settings_validate.add_argument("--cloud", choices=("gcp", "aws", "all"), required=True)
    settings_validate.set_defaults(command_path=("settings", "validate"), handler=handle_settings_validate)

    config = subparsers.add_parser("config", help="Show config locations and merged state.")
    config_subparsers = config.add_subparsers(dest="config_command", required=True)

    config_show = config_subparsers.add_parser("show", help="Show project, local, effective, or path views.")
    group = config_show.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", action="store_true")
    group.add_argument("--local", action="store_true")
    group.add_argument("--effective", action="store_true")
    group.add_argument("--paths", action="store_true")
    config_show.set_defaults(command_path=("config", "show"), handler=handle_config_show)

    config_where_parser = config_subparsers.add_parser("where", help="Show where a config key lives.")
    config_where_parser.add_argument("key")
    config_where_parser.set_defaults(command_path=("config", "where"), handler=handle_config_where)

    config_wizard_parser = config_subparsers.add_parser("wizard", help="Interactive config workflow.")
    config_wizard_parser.set_defaults(command_path=("config", "wizard"), handler=handle_config_wizard)

    template = subparsers.add_parser("template", help="Work with bundled handler templates.")
    template_subparsers = template.add_subparsers(dest="template_command", required=True)
    template_download = template_subparsers.add_parser("download", help="Extract a bundled handler template.")
    template_download.add_argument("--cloud", choices=VALID_CLOUDS, required=True)
    template_download.add_argument("--runtime", choices=VALID_RUNTIMES, required=True)
    template_download.add_argument("--output", required=True)
    template_download.add_argument("--force", action="store_true")
    template_download.set_defaults(command_path=("template", "download"), handler=handle_template_download)

    infra = subparsers.add_parser("infra", help="Generate and run Terraform workflow steps.")
    infra_subparsers = infra.add_subparsers(dest="infra_command", required=True)
    for name, handler in (
        ("generate", handle_infra_generate),
        ("plan", handle_infra_plan),
        ("apply", handle_infra_apply),
    ):
        command = infra_subparsers.add_parser(name, help=f"Run `triage infra {name}`.")
        command.add_argument("--cloud", choices=VALID_CLOUDS)
        command.add_argument("--runtime", choices=VALID_RUNTIMES, required=True)
        if name == "apply":
            command.add_argument("--handler-path", required=True)
        command.set_defaults(command_path=("infra", name), handler=handler)

    run_parser = subparsers.add_parser("run", help="Replay the selected handler locally.")
    run_parser.add_argument("--cloud", choices=VALID_CLOUDS)
    run_parser.add_argument("--runtime", choices=VALID_RUNTIMES, required=True)
    run_parser.add_argument("--handler-path", required=True)
    run_parser.add_argument("--input", default="-")
    run_parser.set_defaults(command_path=("run",), handler=handle_run)

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
