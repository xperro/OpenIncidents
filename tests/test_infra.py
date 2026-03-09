import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from triage.constants import VERSION
from triage.infra import generate_infra, package_handler, terraform_main
from triage.project import default_project_config


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class InfraTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.TemporaryDirectory()
        self.handler_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.work_dir.cleanup)
        self.addCleanup(self.handler_dir.cleanup)

    def test_gcp_package_handler_bootstraps_repo_and_builds_image(self):
        source = REPO_ROOT / "triage" / "templates" / "go" / "gcp"
        shutil.copytree(source, self.handler_dir.name, dirs_exist_ok=True)
        pathlib.Path(self.handler_dir.name, ".env").write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
        pathlib.Path(self.handler_dir.name, ".env.local").write_text("SLACK_WEBHOOK_URL=secret\n", encoding="utf-8")
        project = default_project_config(cloud="gcp", env="dev")
        generate_infra(self.work_dir.name, project, "gcp", "go")

        commands = []

        def fake_run(command, cwd=None, env=None, input_text=None):
            commands.append((command, cwd))
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with mock.patch("triage.infra.run_subprocess", side_effect=fake_run):
            artifact = package_handler(
                self.work_dir.name,
                "gcp",
                "go",
                self.handler_dir.name,
                project,
            )

        self.assertTrue(
            artifact["artifact_reference"].startswith(
                f"us-central1-docker.pkg.dev/my-project/triage/triage-handler:go-dev-{VERSION}-"
            )
        )
        self.assertTrue(os.path.exists(os.path.join(artifact["build_context_dir"], "Dockerfile")))
        self.assertFalse(os.path.exists(os.path.join(artifact["build_context_dir"], ".env")))
        self.assertFalse(os.path.exists(os.path.join(artifact["build_context_dir"], ".env.local")))
        self.assertEqual(commands[0][0][:3], ["terraform", "init", "-input=false"])
        self.assertEqual(commands[1][0][0:2], ["terraform", "apply"])
        self.assertEqual(commands[2][0][0:3], ["gcloud", "builds", "submit"])

    def test_gcp_terraform_template_contains_real_resources(self):
        rendered = terraform_main("gcp")

        self.assertIn('resource "google_cloud_run_v2_service" "handler"', rendered)
        self.assertIn('resource "google_logging_project_sink" "logs"', rendered)
        self.assertIn('resource "google_pubsub_subscription" "push"', rendered)
        self.assertIn('resource "google_artifact_registry_repository" "handler"', rendered)
        self.assertIn('for_each = local.gcp_sinks', rendered)
        self.assertIn('name  = "TRIAGE_GCP_SINK_ROUTING"', rendered)
        self.assertIn('name = var.topic_name', rendered)
        self.assertIn('topic = google_pubsub_topic.logs.name', rendered)
        self.assertNotIn('repo_name=${urlencode(each.value.repo_name)}', rendered)
        self.assertIn('dynamic "exclusions"', rendered)
        self.assertNotIn('name  = "PORT"', rendered)


if __name__ == "__main__":
    unittest.main()
