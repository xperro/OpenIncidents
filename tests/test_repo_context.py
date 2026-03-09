import os
import tempfile
import unittest

from triage.llm_prep.repo_context import RepoSource, scan_repo_for_terms


class RepoContextTests(unittest.TestCase):
    def test_scan_repo_skips_wrapper_files_and_prefers_business_paths(self):
        with tempfile.TemporaryDirectory(prefix="triage-repo-") as repo_dir:
            os.makedirs(os.path.join(repo_dir, "internal", "approvals"), exist_ok=True)
            with open(os.path.join(repo_dir, "mvnw"), "w", encoding="utf-8") as handle:
                handle.write("timeout timeout timeout\n")
            with open(
                os.path.join(repo_dir, "internal", "approvals", "repository.go"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    "package approvals\n"
                    "func LoadApproval() error {\n"
                    "  return timeoutErr\n"
                    "}\n"
                )

            repo = RepoSource(repo_name="tmp", repo_dir=repo_dir, repo_url="", branch="main")
            matches = scan_repo_for_terms(
                repo,
                ["timeout"],
                max_files=3,
                max_snippet_lines=20,
                max_snippet_chars=1000,
            )

            self.assertTrue(matches)
            paths = [item["file_path"] for item in matches]
            self.assertIn("internal/approvals/repository.go", paths)
            self.assertNotIn("mvnw", paths)


if __name__ == "__main__":
    unittest.main()
