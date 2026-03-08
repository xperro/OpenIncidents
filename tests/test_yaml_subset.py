import unittest

from triage.project import default_project_config, normalize_project_config, render_project_config
from triage.yaml_subset import load_yaml


class YamlSubsetTests(unittest.TestCase):
    def test_round_trip_project_config(self):
        config = default_project_config(cloud="aws", llm_provider="openai", llm_model="gpt-4.1")
        config["repos"] = [
            {
                "name": "payments-orchestrator",
                "git_url": "https://github.com/example/payments-orchestrator.git",
                "auth": {
                    "username_env": "GIT_USERNAME",
                    "token_env": "GIT_TOKEN",
                },
                "local_path": ".triage/repos/payments-orchestrator",
                "branch": "main",
            }
        ]

        rendered = render_project_config(config)
        loaded = normalize_project_config(load_yaml(rendered))

        self.assertEqual(loaded["cloud"], "aws")
        self.assertEqual(loaded["llm"]["provider"], "openai")
        self.assertEqual(loaded["repos"][0]["auth"]["token_env"], "GIT_TOKEN")
        self.assertIn("repos:\n  - name: payments-orchestrator", rendered)


if __name__ == "__main__":
    unittest.main()
