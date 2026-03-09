import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import zipapp
import unittest
import zipfile


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class ReleaseBuilderTests(unittest.TestCase):
    def test_build_release_outputs_expected_assets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "build_release.py"),
                    "--output-dir",
                    temp_dir,
                    "--repository",
                    "xperro/OpenIncidents",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            manifest = json.loads(result.stdout)
            assets_dir = pathlib.Path(manifest["assets_dir"])
            self.assertTrue((assets_dir / "triage.pyz").exists())
            self.assertTrue((assets_dir / "triage").exists())
            self.assertTrue((assets_dir / "triage.cmd").exists())
            self.assertTrue(
                (assets_dir / f"triage_{manifest['version']}_homebrew.rb").exists()
            )

            help_result = subprocess.run(
                [sys.executable, str(assets_dir / "triage.pyz"), "--help"],
                check=False,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            self.assertEqual(help_result.returncode, 0, msg=help_result.stderr)
            self.assertIn("usage: triage", help_result.stdout)

            bundle_tar = assets_dir / f"triage_{manifest['version']}_bundle.tar.gz"
            with tarfile.open(bundle_tar, "r:gz") as archive:
                names = archive.getnames()
            self.assertIn("triage.pyz", names)
            self.assertIn("triage", names)
            self.assertIn("triage.cmd", names)

            bundle_zip = assets_dir / f"triage_{manifest['version']}_bundle.zip"
            with zipfile.ZipFile(bundle_zip, "r") as archive:
                names = archive.namelist()
            self.assertIn("triage.pyz", names)

            with zipfile.ZipFile(assets_dir / "triage.pyz", "r") as archive:
                names = archive.namelist()
            self.assertIn("triage/templates/python/gcp/main.py", names)
            self.assertIn("triage/templates/go/aws/go.mod", names)

            formula = (assets_dir / f"triage_{manifest['version']}_homebrew.rb").read_text(
                encoding="utf-8"
            )
            self.assertIn("class Triage < Formula", formula)
            self.assertIn(f"triage_{manifest['version']}_bundle.tar.gz", formula)
            self.assertIn('depends_on "python"', formula)

    def test_build_release_rejects_tag_version_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "build_release.py"),
                    "--output-dir",
                    temp_dir,
                    "--tag",
                    "v9.9.9",
                    "--repository",
                    "xperro/OpenIncidents",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match source version", result.stderr)


if __name__ == "__main__":
    unittest.main()
