#!/usr/bin/env python3
"""Build portable release assets for the ``triage`` CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import stat
import sys
import tarfile
import tempfile
import zipapp
import zipfile


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LAUNCHERS_DIR = REPO_ROOT / "packaging" / "launchers"
CLI_SOURCE_DIR = REPO_ROOT / "triage"
TEMPLATES_DIR = CLI_SOURCE_DIR / "templates"
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store", ".git"}
IGNORED_SUFFIXES = (".pyc", ".pyo", ".tmp", ".swp")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tag", help="Git tag to validate against, for example v1.0.1")
    return parser.parse_args(argv)


def load_version() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from triage.constants import VERSION
    finally:
        sys.path.pop(0)
    return VERSION


def normalize_version(tag: str | None, version: str) -> str:
    if tag is None:
        return version
    if not tag.startswith("v"):
        raise SystemExit("error: release tag must start with `v`.")
    tag_version = tag[1:]
    if tag_version != version:
        raise SystemExit(
            f"error: release tag version `{tag_version}` does not match source version `{version}`."
        )
    return tag_version


def should_skip(path: pathlib.Path) -> bool:
    if path.name in IGNORED_NAMES:
        return True
    return any(path.name.endswith(suffix) for suffix in IGNORED_SUFFIXES)


def copy_tree(source: pathlib.Path, target: pathlib.Path) -> None:
    for root, dirnames, filenames in os.walk(source):
        dirnames[:] = [name for name in dirnames if not should_skip(pathlib.Path(name))]
        root_path = pathlib.Path(root)
        relative_root = root_path.relative_to(source)
        target_root = target / relative_root
        target_root.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            source_file = root_path / filename
            if should_skip(source_file):
                continue
            shutil.copy2(source_file, target_root / filename)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_executable(path: pathlib.Path) -> None:
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_pyz(target_path: pathlib.Path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_root = pathlib.Path(temp_dir) / "zipapp-src"
        staging_root.mkdir(parents=True, exist_ok=True)
        copy_tree(CLI_SOURCE_DIR, staging_root / "triage")
        zipapp.create_archive(
            staging_root,
            target=target_path,
            main="triage.cli:main",
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    make_executable(target_path)


def build_archives(bundle_root: pathlib.Path, assets_dir: pathlib.Path, version: str) -> tuple[pathlib.Path, pathlib.Path]:
    tar_path = assets_dir / f"triage_{version}_bundle.tar.gz"
    zip_path = assets_dir / f"triage_{version}_bundle.zip"

    with tarfile.open(tar_path, "w:gz") as archive:
        for child in sorted(bundle_root.iterdir()):
            archive.add(child, arcname=child.name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for child in sorted(bundle_root.rglob("*")):
            if child.is_dir():
                continue
            archive.write(child, arcname=str(child.relative_to(bundle_root)))

    return tar_path, zip_path


def write_checksums(assets: list[pathlib.Path], target_path: pathlib.Path) -> None:
    lines = [f"{sha256_file(asset)}  {asset.name}" for asset in assets]
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_release(output_dir: pathlib.Path, tag: str | None) -> dict[str, object]:
    version = normalize_version(tag, load_version())
    assets_dir = output_dir / "assets"
    bundle_root = output_dir / "bundle"
    assets_dir.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)

    pyz_path = assets_dir / "triage.pyz"
    build_pyz(pyz_path)

    unix_launcher = assets_dir / "triage"
    windows_launcher = assets_dir / "triage.cmd"
    shutil.copy2(LAUNCHERS_DIR / "triage", unix_launcher)
    shutil.copy2(LAUNCHERS_DIR / "triage.cmd", windows_launcher)
    make_executable(unix_launcher)

    shutil.copy2(pyz_path, bundle_root / "triage.pyz")
    shutil.copy2(unix_launcher, bundle_root / "triage")
    shutil.copy2(windows_launcher, bundle_root / "triage.cmd")
    make_executable(bundle_root / "triage")

    tar_path, zip_path = build_archives(bundle_root, assets_dir, version)
    checksums_path = assets_dir / f"triage_{version}_sha256sums.txt"
    write_checksums(
        [pyz_path, unix_launcher, windows_launcher, tar_path, zip_path],
        checksums_path,
    )

    manifest = {
        "version": version,
        "tag": tag,
        "assets_dir": str(assets_dir),
        "bundle_root": str(bundle_root),
        "assets": [
            "triage.pyz",
            "triage",
            "triage.cmd",
            tar_path.name,
            zip_path.name,
            checksums_path.name,
        ],
        "templates_included": TEMPLATES_DIR.is_dir(),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = pathlib.Path(args.output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_release(output_dir, args.tag)
    sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
