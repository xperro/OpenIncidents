import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from triage.cli import main
from triage.constants import VERSION
from triage.errors import UserError
from triage.infra import package_handler
from triage.project import default_project_config, save_project_config
from triage.state import new_state, save_state, state_path
from triage.validation import ValidationResult


class TtyInput(io.StringIO):
    def isatty(self):
        return True


class InterruptingInput:
    def readline(self):
        raise KeyboardInterrupt


class CliTests(unittest.TestCase):
    def setUp(self):
        self.home_dir = tempfile.mkdtemp(prefix="triage-home-")
        self.work_dir = tempfile.mkdtemp(prefix="triage-work-")
        self.addCleanup(self._cleanup_tree, self.work_dir)
        self.addCleanup(self._cleanup_tree, self.home_dir)
        patcher = mock.patch.dict(
            os.environ,
            {
                "HOME": self.home_dir,
                "APPDATA": self.home_dir,
                "USERPROFILE": self.home_dir,
                "LOCALAPPDATA": self.home_dir,
                "GOTELEMETRY": "off",
                "GOTOOLCHAIN": "local",
                "TRIAGE_REPO_URLS": "",
                "TRIAGE_LLM_COST_PROFILE": "",
                "TRIAGE_LLM_MODEL": "",
                "TRIAGE_OPENAI_MODEL": "",
                "TRIAGE_ANTHROPIC_MODEL": "",
                "TRIAGE_LANGUAGE": "",
            },
            clear=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _cleanup_tree(self, path: str) -> None:
        if not os.path.exists(path):
            return
        last_error = None
        for _ in range(6):
            try:
                shutil.rmtree(path)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5)
        if os.name == "nt":
            shutil.rmtree(path, ignore_errors=True)
            return
        if last_error is not None:
            raise last_error

    def run_cli(self, argv, input_text=""):
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = main(
            argv=argv,
            cwd=self.work_dir,
            stdin=io.StringIO(input_text),
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    def complete_bootstrap(self):
        state = new_state()
        state["default_cloud"] = "gcp"
        state["clouds"]["gcp"]["enabled"] = True
        state["llm"]["provider"] = "none"
        save_state(state)

    def test_infra_generate_is_blocked_before_init(self):
        code, _, stderr = self.run_cli(
            ["infra", "generate", "--cloud", "gcp", "--runtime", "python"]
        )

        self.assertEqual(code, 1)
        self.assertIn("Local CLI state does not exist yet", stderr)

    def test_llm_prep_runs_without_init(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        code, stdout, stderr = self.run_cli(
            ["llm-prep", "--cloud", "gcp", "--runtime", "python"],
            input_text=payload,
        )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertEqual(prepared["meta"]["prepared_incidents"], 1)
        self.assertEqual(prepared["incidents"][0]["service"], "payments-orchestrator")

    def test_llm_prep_lean_cost_profile_truncates_context(self):
        long_message = ("timeout on postgres while fetching approvals " * 120).strip()
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": long_message,
            }
        )
        code, stdout, stderr = self.run_cli(
            ["llm-prep", "--cloud", "gcp", "--runtime", "python", "--cost-profile", "lean"],
            input_text=payload,
        )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertEqual(prepared["meta"]["cost_profile"], "lean")
        summary = prepared["incidents"][0]["summary"]
        self.assertEqual(len(summary), 1200)

    def test_llm_prep_uses_cost_profile_from_env_when_flag_missing(self):
        long_message = ("timeout on postgres while fetching approvals " * 120).strip()
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": long_message,
            }
        )
        with mock.patch.dict(os.environ, {"TRIAGE_LLM_COST_PROFILE": "lean"}, clear=False):
            code, stdout, stderr = self.run_cli(
                ["llm-prep", "--cloud", "gcp", "--runtime", "python"],
                input_text=payload,
            )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertEqual(prepared["meta"]["cost_profile"], "lean")
        self.assertEqual(len(prepared["incidents"][0]["summary"]), 1200)

    def test_llm_prep_cost_profile_flag_overrides_env(self):
        long_message = ("timeout on postgres while fetching approvals " * 120).strip()
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": long_message,
            }
        )
        with mock.patch.dict(os.environ, {"TRIAGE_LLM_COST_PROFILE": "lean"}, clear=False):
            code, stdout, stderr = self.run_cli(
                ["llm-prep", "--cloud", "gcp", "--runtime", "python", "--cost-profile", "deep"],
                input_text=payload,
            )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertEqual(prepared["meta"]["cost_profile"], "deep")
        self.assertEqual(len(prepared["incidents"][0]["summary"]), 4000)

    def test_llm_prep_loads_repo_urls_from_env_array(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        fake_repo_source = mock.Mock(
            repo_name="sample-repo",
            repo_url="https://github.com/example/sample-repo.git",
            branch="main",
            repo_dir="/tmp/sample-repo",
        )
        with mock.patch.dict(
            os.environ,
            {"TRIAGE_REPO_URLS": '["https://github.com/example/sample-repo.git"]'},
            clear=False,
        ):
            with mock.patch("triage.cli.checkout_repo", return_value=fake_repo_source) as checkout:
                code, stdout, stderr = self.run_cli(
                    ["llm-prep", "--cloud", "gcp", "--runtime", "python"],
                    input_text=payload,
                )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertTrue(prepared["meta"]["repo_context_enabled"])
        checkout.assert_called_once()
        self.assertEqual(checkout.call_args.args[1], "https://github.com/example/sample-repo.git")

    def test_llm_prep_loads_repo_urls_from_project_config_with_auth_env(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "db timeout on postgres",
            }
        )
        project = default_project_config()
        project["repos"] = [
            {
                "name": "payments",
                "git_url": "https://github.com/example/payments.git",
                "branch": "develop",
                "auth": {"username_env": "GIT_USERNAME", "token_env": "GIT_TOKEN"},
            }
        ]
        save_project_config(self.work_dir, project)
        fake_repo_source = mock.Mock(
            repo_name="payments",
            repo_url="https://github.com/example/payments.git",
            branch="develop",
            repo_dir="/tmp/payments",
        )
        with mock.patch.dict(
            os.environ,
            {"GIT_USERNAME": "bot-user", "GIT_TOKEN": "tok-123"},
            clear=False,
        ):
            with mock.patch("triage.cli.checkout_repo", return_value=fake_repo_source) as checkout:
                code, stdout, stderr = self.run_cli(
                    ["llm-prep", "--cloud", "gcp", "--runtime", "python"],
                    input_text=payload,
                )

        self.assertEqual(code, 0, msg=stderr)
        prepared = json.loads(stdout)
        self.assertTrue(prepared["meta"]["repo_context_enabled"])
        checkout.assert_called_once()
        self.assertEqual(checkout.call_args.args[1], "https://github.com/example/payments.git")
        self.assertEqual(checkout.call_args.kwargs["branch"], "develop")
        self.assertEqual(
            checkout.call_args.kwargs["clone_url"],
            "https://bot-user:tok-123@github.com/example/payments.git",
        )

    def test_llm_request_and_client_mock_run_without_init(self):
        prepared_path = os.path.join(self.work_dir, "prepared.json")
        request_path = os.path.join(self.work_dir, "request.json")
        analysis_path = os.path.join(self.work_dir, "analysis.json")

        prepared_payload = {
            "schema_version": "llm-prep.v1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "cloud": "gcp",
                    "runtime_hint": "go",
                    "severity": "ERROR",
                    "count": 1,
                    "window": {"first_seen": "2026-03-09T15:00:00Z", "last_seen": "2026-03-09T15:00:00Z"},
                    "summary": "db timeout on postgres",
                    "error_message": "db timeout on postgres",
                    "stacktrace_excerpt": "",
                    "source_link": "",
                    "llm_input": {"incident_summary": "db timeout on postgres", "evidence": ["event-1"]},
                }
            ],
        }
        with open(prepared_path, "w", encoding="utf-8") as handle:
            json.dump(prepared_payload, handle)

        code, _, stderr = self.run_cli(
            [
                "llm-request",
                "--input",
                prepared_path,
                "--provider",
                "mock",
                "--model",
                "mock-1",
                "--output",
                request_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)
        self.assertTrue(os.path.exists(request_path))

        code, _, stderr = self.run_cli(
            [
                "llm-client",
                "--input",
                request_path,
                "--provider",
                "mock",
                "--output",
                analysis_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)
        self.assertTrue(os.path.exists(analysis_path))
        with open(analysis_path, "r", encoding="utf-8") as handle:
            analysis = json.load(handle)
        self.assertEqual(analysis["schema_version"], "llm-analysis.v1")
        self.assertEqual(analysis["meta"]["analyzed_incidents"], 1)

    def test_llm_resolve_runs_end_to_end_with_mock_without_init(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        artifact_dir = os.path.join(self.work_dir, "resolve-artifacts")
        code, stdout, stderr = self.run_cli(
            [
                "llm-resolve",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--provider",
                "mock",
                "--artifact-dir",
                artifact_dir,
            ],
            input_text=payload,
        )
        self.assertEqual(code, 0, msg=stderr)
        analysis = json.loads(stdout)
        self.assertEqual(analysis["schema_version"], "llm-analysis.v1")
        self.assertTrue(os.path.exists(os.path.join(artifact_dir, "prepared.json")))
        self.assertTrue(os.path.exists(os.path.join(artifact_dir, "llm-request.json")))
        self.assertTrue(os.path.exists(os.path.join(artifact_dir, "llm-analysis.json")))

    def test_llm_resolve_with_notify_writes_notify_artifact(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        artifact_dir = os.path.join(self.work_dir, "resolve-notify-artifacts")
        fake_notify = {
            "schema_version": "llm-notify.v1",
            "targets": ["discord"],
            "dry_run": True,
            "results": [{"target": "discord", "status": "simulated"}],
            "meta": {"attempted": 1, "sent": 0, "simulated": 1, "skipped": 0},
        }
        with mock.patch("triage.cli.notify_analysis", return_value=fake_notify):
            code, stdout, stderr = self.run_cli(
                [
                    "llm-resolve",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                    "--provider",
                    "mock",
                    "--notify",
                    "--notify-target",
                    "discord",
                    "--notify-dry-run",
                    "--artifact-dir",
                    artifact_dir,
                ],
                input_text=payload,
            )
        self.assertEqual(code, 0, msg=stderr)
        self.assertEqual(json.loads(stdout)["schema_version"], "llm-analysis.v1")
        self.assertTrue(os.path.exists(os.path.join(artifact_dir, "llm-notify.json")))

    def test_notify_command_works_with_dry_run(self):
        analysis_path = os.path.join(self.work_dir, "llm-analysis.json")
        analysis_payload = {
            "schema_version": "llm-analysis.v1",
            "results": [
                {
                    "incident_id": "abc123",
                    "provider": "mock",
                    "model": "mock-1",
                    "analysis": {
                        "summary": "Timeout on DB",
                        "suspected_cause": "Pool saturation",
                        "suggested_fix": "Tune pool and query",
                        "confidence": 0.7,
                        "safe_to_escalate": True,
                        "files_or_area_to_check": ["internal/db/repo.go"],
                        "tests_to_run": ["integration"],
                    },
                }
            ],
        }
        with open(analysis_path, "w", encoding="utf-8") as handle:
            json.dump(analysis_payload, handle)
        with mock.patch.dict(
            os.environ,
            {"DISCORD_WEBHOOK_URL": "https://discord.example/webhook"},
            clear=False,
        ):
            code, stdout, stderr = self.run_cli(
                ["notify", "--input", analysis_path, "--target", "discord", "--dry-run"]
            )
        self.assertEqual(code, 0, msg=stderr)
        report = json.loads(stdout)
        self.assertEqual(report["schema_version"], "llm-notify.v1")
        self.assertEqual(report["meta"]["simulated"], 1)

    def test_llm_resolve_auto_provider_prefers_openai_when_both_keys_exist(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        artifact_dir = os.path.join(self.work_dir, "resolve-artifacts-auto-openai")
        fake_analysis = {
            "schema_version": "llm-analysis.v1",
            "request_id": "x",
            "analyzed_at": "2026-03-09T00:00:00Z",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "results": [],
            "meta": {"input_incidents": 1, "analyzed_incidents": 0},
        }
        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "ant-test"},
            clear=False,
        ):
            with mock.patch("triage.cli.run_llm_client", return_value=fake_analysis) as run_client:
                code, stdout, stderr = self.run_cli(
                    [
                        "llm-resolve",
                        "--cloud",
                        "gcp",
                        "--runtime",
                        "python",
                        "--artifact-dir",
                        artifact_dir,
                    ],
                    input_text=payload,
                )
        self.assertEqual(code, 0, msg=stderr)
        self.assertEqual(json.loads(stdout)["provider"], "openai")
        self.assertEqual(run_client.call_args.kwargs["provider"], "openai")

    def test_llm_resolve_auto_provider_falls_back_to_mock_without_keys(self):
        payload = json.dumps(
            {
                "severity": "ERROR",
                "resource": {"labels": {"service_name": "payments-orchestrator"}},
                "textPayload": "gateway timeout while charging card",
            }
        )
        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""},
            clear=False,
        ):
            code, stdout, stderr = self.run_cli(
                [
                    "llm-resolve",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                ],
                input_text=payload,
            )
        self.assertEqual(code, 0, msg=stderr)
        self.assertEqual(json.loads(stdout)["provider"], "mock")

    def test_llm_request_uses_openai_default_model_when_missing(self):
        prepared_path = os.path.join(self.work_dir, "prepared.json")
        request_path = os.path.join(self.work_dir, "request.json")
        prepared_payload = {
            "schema_version": "llm-prep.v1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "cloud": "gcp",
                    "runtime_hint": "go",
                    "severity": "ERROR",
                    "count": 1,
                    "window": {"first_seen": "2026-03-09T15:00:00Z", "last_seen": "2026-03-09T15:00:00Z"},
                    "summary": "db timeout on postgres",
                    "error_message": "db timeout on postgres",
                    "stacktrace_excerpt": "",
                    "source_link": "",
                    "llm_input": {"incident_summary": "db timeout on postgres", "evidence": ["event-1"]},
                }
            ],
        }
        with open(prepared_path, "w", encoding="utf-8") as handle:
            json.dump(prepared_payload, handle)
        code, _, stderr = self.run_cli(
            [
                "llm-request",
                "--input",
                prepared_path,
                "--provider",
                "openai",
                "--output",
                request_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)
        with open(request_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["model"], "gpt-4o-mini")

    def test_llm_request_uses_model_from_env_when_missing(self):
        prepared_path = os.path.join(self.work_dir, "prepared.json")
        request_path = os.path.join(self.work_dir, "request.json")
        prepared_payload = {
            "schema_version": "llm-prep.v1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "cloud": "gcp",
                    "runtime_hint": "go",
                    "severity": "ERROR",
                    "count": 1,
                    "window": {"first_seen": "2026-03-09T15:00:00Z", "last_seen": "2026-03-09T15:00:00Z"},
                    "summary": "db timeout on postgres",
                    "error_message": "db timeout on postgres",
                    "stacktrace_excerpt": "",
                    "source_link": "",
                    "llm_input": {"incident_summary": "db timeout on postgres", "evidence": ["event-1"]},
                }
            ],
        }
        with open(prepared_path, "w", encoding="utf-8") as handle:
            json.dump(prepared_payload, handle)
        with mock.patch.dict(os.environ, {"TRIAGE_LLM_MODEL": "gpt-4.1-mini"}, clear=False):
            code, _, stderr = self.run_cli(
                [
                    "llm-request",
                    "--input",
                    prepared_path,
                    "--provider",
                    "openai",
                    "--output",
                    request_path,
                ]
            )
        self.assertEqual(code, 0, msg=stderr)
        with open(request_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["model"], "gpt-4.1-mini")

    def test_llm_request_uses_anthropic_provider_specific_env_model(self):
        prepared_path = os.path.join(self.work_dir, "prepared.json")
        request_path = os.path.join(self.work_dir, "request.json")
        prepared_payload = {
            "schema_version": "llm-prep.v1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "cloud": "gcp",
                    "runtime_hint": "go",
                    "severity": "ERROR",
                    "count": 1,
                    "window": {"first_seen": "2026-03-09T15:00:00Z", "last_seen": "2026-03-09T15:00:00Z"},
                    "summary": "db timeout on postgres",
                    "error_message": "db timeout on postgres",
                    "stacktrace_excerpt": "",
                    "source_link": "",
                    "llm_input": {"incident_summary": "db timeout on postgres", "evidence": ["event-1"]},
                }
            ],
        }
        with open(prepared_path, "w", encoding="utf-8") as handle:
            json.dump(prepared_payload, handle)
        with mock.patch.dict(
            os.environ,
            {
                "TRIAGE_LLM_MODEL": "global-fallback-model",
                "TRIAGE_ANTHROPIC_MODEL": "claude-3-5-haiku",
            },
            clear=False,
        ):
            code, _, stderr = self.run_cli(
                [
                    "llm-request",
                    "--input",
                    prepared_path,
                    "--provider",
                    "anthropic",
                    "--output",
                    request_path,
                ]
            )
        self.assertEqual(code, 0, msg=stderr)
        with open(request_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["model"], "claude-3-5-haiku")

    def test_init_creates_state_and_scaffold(self):
        fake_validation = ValidationResult(cloud="gcp", ok=True, checks=["gcloud: ok"])
        with mock.patch("triage.cli.validate_cloud", return_value=fake_validation):
            code, stdout, stderr = self.run_cli(["init"], input_text="gcp\nnone\n")

        self.assertEqual(code, 0, msg=stderr)
        self.assertIn("Local state:", stdout)
        self.assertTrue(os.path.exists(os.path.join(self.work_dir, "triage.yaml")))
        self.assertTrue(os.path.exists(state_path()))

    def test_help_alias_prints_root_help(self):
        code, stdout, stderr = self.run_cli(["h"])

        self.assertEqual(code, 0, msg=stderr)
        self.assertIn("Bootstrap local state, inspect configuration", stdout)
        self.assertIn("triage help infra apply", stdout)
        self.assertEqual("", stderr)

    def test_nested_help_command_prints_target_help(self):
        code, stdout, stderr = self.run_cli(["help", "infra", "apply"])

        self.assertEqual(code, 0, msg=stderr)
        self.assertIn("usage: triage infra apply", stdout)
        self.assertIn("--handler-path", stdout)
        self.assertIn("triage infra apply --cloud gcp --runtime go --handler-path /abs/path", stdout)
        self.assertEqual("", stderr)

    def test_settings_without_subcommand_prints_contextual_help(self):
        code, stdout, stderr = self.run_cli(["settings"])

        self.assertEqual(code, 2)
        self.assertEqual("", stdout)
        self.assertIn("usage: triage settings", stderr)
        self.assertIn("choose one `settings` command", stderr)
        self.assertNotIn("settings_command", stderr)

    def test_infra_without_subcommand_prints_contextual_help(self):
        code, stdout, stderr = self.run_cli(["infra"])

        self.assertEqual(code, 2)
        self.assertEqual("", stdout)
        self.assertIn("usage: triage infra", stderr)
        self.assertIn("choose one `infra` command", stderr)
        self.assertNotIn("infra_command", stderr)

    def test_parse_errors_point_to_command_help(self):
        code, stdout, stderr = self.run_cli(["run"])

        self.assertEqual(code, 2)
        self.assertEqual("", stdout)
        self.assertIn("triage run: error: the following arguments are required", stderr)
        self.assertIn("hint: run `triage run -h` for usage examples.", stderr)

    def test_keyboard_interrupt_is_handled_cleanly(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        code = main(
            argv=["init"],
            cwd=self.work_dir,
            stdin=InterruptingInput(),
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(code, 130)
        self.assertIn("Validate which cloud now", stdout.getvalue())
        self.assertEqual("Interrupted.\n", stderr.getvalue())

    def test_template_download_writes_expected_files(self):
        self.complete_bootstrap()
        output_path = os.path.join(self.work_dir, "handler-template")
        code, stdout, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                output_path,
            ]
        )

        self.assertEqual(code, 0, msg=stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["output_path"], output_path)
        self.assertTrue(
            payload["source_path"].endswith(os.path.join("triage", "templates", "python", "gcp"))
        )
        self.assertTrue(os.path.exists(os.path.join(output_path, "main.py")))
        self.assertTrue(os.path.exists(os.path.join(output_path, "app.py")))
        self.assertTrue(os.path.exists(os.path.join(output_path, "requirements.txt")))
        self.assertTrue(os.path.exists(os.path.join(output_path, "adapters", "gcp.py")))
        self.assertFalse(os.path.exists(os.path.join(output_path, "lambda_entrypoint.py")))

    def test_template_download_requires_force_for_non_empty_dir(self):
        self.complete_bootstrap()
        output_path = os.path.join(self.work_dir, "handler-template")
        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, "keep.txt"), "w", encoding="utf-8") as handle:
            handle.write("occupied")

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                output_path,
            ]
        )

        self.assertEqual(code, 1)
        self.assertIn("Output directory is not empty", stderr)

    def test_template_download_rejects_relative_output_path(self):
        self.complete_bootstrap()

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                "relative-template-path",
            ]
        )

        self.assertEqual(code, 1)
        self.assertIn("`--output` must be an absolute path", stderr)

    def test_template_download_force_overwrites_dir(self):
        self.complete_bootstrap()
        output_path = os.path.join(self.work_dir, "handler-template")
        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, "stale.txt"), "w", encoding="utf-8") as handle:
            handle.write("stale")

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "aws",
                "--runtime",
                "python",
                "--output",
                output_path,
                "--force",
            ]
        )

        self.assertEqual(code, 0, msg=stderr)
        self.assertFalse(os.path.exists(os.path.join(output_path, "stale.txt")))
        self.assertTrue(os.path.exists(os.path.join(output_path, "lambda_entrypoint.py")))

    def test_template_download_filters_junk_files(self):
        self.complete_bootstrap()
        custom_root = os.path.join(self.work_dir, "custom-templates")
        source_dir = os.path.join(custom_root, "python", "gcp")
        os.makedirs(os.path.join(source_dir, "__pycache__"), exist_ok=True)
        os.makedirs(os.path.join(source_dir, "adapters"), exist_ok=True)
        with open(os.path.join(source_dir, "requirements.txt"), "w", encoding="utf-8") as handle:
            handle.write("starlette==0.46.2\n")
        with open(os.path.join(source_dir, "main.py"), "w", encoding="utf-8") as handle:
            handle.write("print('ok')\n")
        with open(os.path.join(source_dir, "app.py"), "w", encoding="utf-8") as handle:
            handle.write("app = None\n")
        with open(os.path.join(source_dir, "adapters", "gcp.py"), "w", encoding="utf-8") as handle:
            handle.write("SUMMARY = True\n")
        with open(os.path.join(source_dir, "adapters", "local.py"), "w", encoding="utf-8") as handle:
            handle.write("def read_input(*_): return ''\n")
        with open(os.path.join(source_dir, "__pycache__", "junk.pyc"), "wb") as handle:
            handle.write(b"junk")
        with open(os.path.join(source_dir, ".DS_Store"), "w", encoding="utf-8") as handle:
            handle.write("junk")

        output_path = os.path.join(self.work_dir, "downloaded-template")
        with mock.patch("triage.templates.resolve_templates_root", return_value=custom_root):
            code, _, stderr = self.run_cli(
                [
                    "template",
                    "download",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                    "--output",
                    output_path,
                ]
            )

        self.assertEqual(code, 0, msg=stderr)
        self.assertTrue(os.path.exists(os.path.join(output_path, "main.py")))
        self.assertFalse(os.path.exists(os.path.join(output_path, ".DS_Store")))
        self.assertFalse(os.path.exists(os.path.join(output_path, "__pycache__")))

    def test_infra_generate_writes_terraform_inputs(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["gcp"]["sinks"] = [
            {
                "name": "approve-mrs-dev",
                "repo_name": "approve-mrs-dev",
                "description": "Approve MRs service logs.",
                "include_severity_at_or_above": "INFO",
                "include_repo_name_like": "approve-mrs",
                "exclude_severities": ["DEBUG"],
            }
        ]
        save_project_config(self.work_dir, project)
        with mock.patch(
            "triage.cli.validate_cloud",
            return_value=ValidationResult(cloud="gcp", ok=True, checks=["ok"]),
        ):
            code, stdout, stderr = self.run_cli(
                ["infra", "generate", "--cloud", "gcp", "--runtime", "python"]
            )

        self.assertEqual(code, 0, msg=stderr)
        payload = json.loads(stdout)
        tfvars = os.path.join(payload["infra_dir"], "terraform.tfvars.json")
        with open(tfvars, "r", encoding="utf-8") as handle:
            generated = json.load(handle)
        self.assertEqual(generated["topic_name"], "triage-dev")
        self.assertEqual(generated["subscription_name"], "triage-dev-push")
        self.assertEqual(generated["sinks"][0]["name"], "approve-mrs-dev")
        self.assertEqual(generated["sinks"][0]["repo_name"], "approve-mrs-dev")
        self.assertEqual(generated["sinks"][0]["repo_match_like"], "approve-mrs")
        self.assertIn('severity>=INFO', generated["sinks"][0]["filter"])
        self.assertEqual(generated["sinks"][0]["exclusions"][0]["filter"], "severity=DEBUG")
        self.assertEqual(
            generated["container_image"],
            f"us-central1-docker.pkg.dev/my-project/triage/triage-handler:python-dev-{VERSION}-pending",
        )

    def test_run_executes_python_template_locally(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir, project)
        template_path = os.path.join(self.work_dir, "template")
        os.makedirs(template_path, exist_ok=True)

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                template_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)

        sample_path = os.path.join(template_path, "sample-events", "gcp-pubsub.json")
        with mock.patch(
            "triage.cli.validate_cloud",
            return_value=ValidationResult(cloud="gcp", ok=True, checks=["ok"]),
        ):
            code, stdout, stderr = self.run_cli(
                [
                    "run",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                    "--handler-path",
                    template_path,
                    "--input",
                    sample_path,
                ]
            )

        self.assertEqual(code, 0, msg=stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["returncode"], 0)
        self.assertEqual(payload["stdout_json"]["runtime"], "python")
        self.assertEqual(
            payload["stdout_json"]["logging_event"]["textPayload"],
            "Aprobacion Bitbucket exitosa con credencial #1",
        )
        self.assertEqual(
            payload["stdout_json"]["logging_event"]["resource"]["labels"]["service_name"],
            "approve-mrs-dev",
        )
        self.assertEqual(payload["stdout_json"]["repo_name"], "approve-mrs-dev")
        self.assertEqual(
            payload["stdout_json"]["error_message"],
            "Aprobacion Bitbucket exitosa con credencial #1",
        )

    def test_run_executes_go_template_locally(self):
        if shutil.which("go") is None:
            self.skipTest("go is not installed locally")
        go_version = subprocess.run(
            ["go", "version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if "go1.26.1" not in go_version.stdout:
            self.skipTest("go1.26.1 is not installed locally")

        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir, project)
        template_path = os.path.join(self.work_dir, "go-template")

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "go",
                "--output",
                template_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)

        sample_path = os.path.join(template_path, "sample-events", "gcp-pubsub.json")
        with mock.patch(
            "triage.cli.validate_cloud",
            return_value=ValidationResult(cloud="gcp", ok=True, checks=["ok"]),
        ):
            code, stdout, stderr = self.run_cli(
                [
                    "run",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "go",
                    "--handler-path",
                    template_path,
                    "--input",
                    sample_path,
                ]
            )

        self.assertEqual(code, 0, msg=stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["returncode"], 0)
        self.assertEqual(payload["stdout_json"]["runtime"], "go")
        self.assertEqual(payload["stdout_json"]["cloud"], "gcp")
        self.assertEqual(
            payload["stdout_json"]["logging_event"]["textPayload"],
            "Aprobacion Bitbucket exitosa con credencial #1",
        )
        self.assertEqual(
            payload["stdout_json"]["logging_event"]["resource"]["labels"]["service_name"],
            "approve-mrs-dev",
        )
        self.assertEqual(payload["stdout_json"]["repo_name"], "approve-mrs-dev")
        self.assertEqual(
            payload["stdout_json"]["error_message"],
            "Aprobacion Bitbucket exitosa con credencial #1",
        )

    def test_package_handler_rejects_wrong_variant(self):
        self.complete_bootstrap()
        template_path = os.path.join(self.work_dir, "python-gcp-template")

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                template_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)

        with self.assertRaises(UserError) as ctx:
            package_handler(self.work_dir, "aws", "python", template_path)

        self.assertIn("does not match the expected python/aws template variant", str(ctx.exception))

    def test_run_rejects_relative_handler_path(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir, project)

        with mock.patch(
            "triage.cli.validate_cloud",
            return_value=ValidationResult(cloud="gcp", ok=True, checks=["ok"]),
        ):
            code, _, stderr = self.run_cli(
                [
                    "run",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                    "--handler-path",
                    "relative-handler",
                    "--input",
                    "-",
                ]
            )

        self.assertEqual(code, 1)
        self.assertIn("`--handler-path` must be absolute", stderr)

    def test_run_requires_piped_input_or_explicit_file(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir, project)
        template_path = os.path.join(self.work_dir, "template")

        code, _, stderr = self.run_cli(
            [
                "template",
                "download",
                "--cloud",
                "gcp",
                "--runtime",
                "python",
                "--output",
                template_path,
            ]
        )
        self.assertEqual(code, 0, msg=stderr)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch(
            "triage.cli.validate_cloud",
            return_value=ValidationResult(cloud="gcp", ok=True, checks=["ok"]),
        ):
            code = main(
                argv=[
                    "run",
                    "--cloud",
                    "gcp",
                    "--runtime",
                    "python",
                    "--handler-path",
                    template_path,
                ],
                cwd=self.work_dir,
                stdin=TtyInput(),
                stdout=stdout,
                stderr=stderr,
            )

        self.assertEqual(code, 1)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("No replay payload was provided on stdin", stderr.getvalue())
        self.assertIn("--input /abs/path/to/event.json", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
