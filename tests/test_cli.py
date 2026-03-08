import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from triage.cli import main
from triage.errors import UserError
from triage.infra import package_handler
from triage.project import default_project_config, save_project_config
from triage.state import new_state, save_state, state_path
from triage.validation import ValidationResult


class CliTests(unittest.TestCase):
    def setUp(self):
        self.home_dir = tempfile.TemporaryDirectory()
        self.work_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.home_dir.cleanup)
        self.addCleanup(self.work_dir.cleanup)
        patcher = mock.patch.dict(
            os.environ,
            {
                "HOME": self.home_dir.name,
                "APPDATA": self.home_dir.name,
                "USERPROFILE": self.home_dir.name,
            },
            clear=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, argv, input_text=""):
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = main(
            argv=argv,
            cwd=self.work_dir.name,
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

    def test_init_creates_state_and_scaffold(self):
        fake_validation = ValidationResult(cloud="gcp", ok=True, checks=["gcloud: ok"])
        with mock.patch("triage.cli.validate_cloud", return_value=fake_validation):
            code, stdout, stderr = self.run_cli(["init"], input_text="gcp\nnone\n")

        self.assertEqual(code, 0, msg=stderr)
        self.assertIn("Local state:", stdout)
        self.assertTrue(os.path.exists(os.path.join(self.work_dir.name, "triage.yaml")))
        self.assertTrue(os.path.exists(state_path()))

    def test_template_download_writes_expected_files(self):
        self.complete_bootstrap()
        output_path = os.path.join(self.work_dir.name, "handler-template")
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
        output_path = os.path.join(self.work_dir.name, "handler-template")
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
        output_path = os.path.join(self.work_dir.name, "handler-template")
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
        custom_root = os.path.join(self.work_dir.name, "custom-templates")
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

        output_path = os.path.join(self.work_dir.name, "downloaded-template")
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
        save_project_config(self.work_dir.name, default_project_config())
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
        self.assertEqual(generated["log_filter"], "severity>=ERROR")

    def test_run_executes_python_template_locally(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir.name, project)
        template_path = os.path.join(self.work_dir.name, "template")
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

    def test_run_executes_go_template_locally(self):
        if shutil.which("go") is None:
            self.skipTest("go toolchain is not installed")
        go_version = subprocess.run(
            ["go", "version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if "go1.26.1" not in go_version.stdout:
            self.skipTest("go1.26.1 toolchain is not installed locally")

        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir.name, project)
        template_path = os.path.join(self.work_dir.name, "go-template")

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

    def test_package_handler_rejects_wrong_variant(self):
        self.complete_bootstrap()
        template_path = os.path.join(self.work_dir.name, "python-gcp-template")

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
            package_handler(self.work_dir.name, "aws", "python", template_path)

        self.assertIn("does not match the expected python/aws template variant", str(ctx.exception))

    def test_run_rejects_relative_handler_path(self):
        self.complete_bootstrap()
        project = default_project_config()
        project["integrations"]["slack"]["enabled"] = False
        project["integrations"]["jira"]["enabled"] = False
        save_project_config(self.work_dir.name, project)

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


if __name__ == "__main__":
    unittest.main()
