# OpenIncidents

OpenIncidents is an incident-triage toolkit centered on the `triage` CLI and the `triage-handler` runtime contract.

The repository is still documentation-first: the canonical product and architecture decisions live in [AGENTS.md](AGENTS.md) and in [SPECS/triage/README.md](SPECS/triage/README.md). This README is the operator and contributor entrypoint for the current implementation snapshot.

## Current Status

- `triage` is the CLI, implemented in Python.
- `triage-handler` is the runtime contract used by the official handler templates.
- GCP and AWS are first-class deployment targets.
- Go and Python are the official handler template runtimes.
- The repo already includes:
  - the initial `triage` CLI package under `triage/`
  - official template trees under `triage/templates/`
  - unit tests under `tests/`
  - CI and release workflows under `.github/workflows/`
  - release asset packaging via `scripts/build_release.py`

## Read Order

1. [AGENTS.md](AGENTS.md)
2. [SPECS/triage/README.md](SPECS/triage/README.md)
3. [SPECS/triage/00-product-overview.md](SPECS/triage/00-product-overview.md)
4. [SPECS/triage/01-system-architecture.md](SPECS/triage/01-system-architecture.md)
5. Subsystem specs under [SPECS/triage](SPECS/triage)

## Repository Layout

```text
.
├── AGENTS.md
├── SPECS/triage/
├── triage/
│   ├── cli.py
│   ├── state.py
│   ├── project.py
│   ├── infra.py
│   ├── local_run.py
│   ├── templates.py
│   └── templates/
│       ├── go/
│       │   ├── aws/
│       │   └── gcp/
│       └── python/
│           ├── aws/
│           └── gcp/
├── tests/
├── packaging/launchers/
└── scripts/build_release.py
```

## CLI Surface

The current CLI command surface is:

- `triage init`
- `triage settings show`
- `triage settings set <key> <value>`
- `triage settings validate --cloud gcp|aws|all`
- `triage config show --project|--local|--effective|--paths`
- `triage config where <key>`
- `triage config wizard`
- `triage template download --cloud ... --runtime ... --output /abs/path`
- `triage infra generate --cloud ... --runtime ...`
- `triage infra plan --cloud ... --runtime ...`
- `triage infra apply --cloud ... --runtime ... --handler-path /abs/path`
- `triage run --cloud ... --runtime ... --handler-path /abs/path --input ...`

## Quick Start

### 1. Inspect the CLI

```bash
python3 -m triage --help
```

### 2. Run the test suite

```bash
python3 -m unittest discover -s tests -v
```

### 3. Bootstrap a local project

```bash
python3 -m triage init
```

This creates:

- a local CLI state file outside the repo
- `triage.yaml`
- `.env.example`
- `.triage/` scaffold directories in the working project

### 4. Download an official handler template

```bash
python3 -m triage template download \
  --cloud gcp \
  --runtime python \
  --output /absolute/path/to/triage-handler
```

The official template roots are:

- `triage/templates/go/gcp`
- `triage/templates/go/aws`
- `triage/templates/python/gcp`
- `triage/templates/python/aws`

### 5. Build release assets

```bash
python3 scripts/build_release.py --output-dir dist/local
```

This produces:

- `triage.pyz`
- `triage`
- `triage.cmd`
- versioned `.tar.gz` and `.zip` bundles
- SHA256 checksum output

## CI And Release

- [`.github/workflows/ci.yml`](/Users/cristobalcontreras/GitHub/OpenIncidents/.github/workflows/ci.yml) runs:
  - unit tests on Ubuntu, macOS, and Windows
  - a CLI smoke test with `python -m triage --help`
  - release bundle build and extraction checks
- [`.github/workflows/release.yml`](/Users/cristobalcontreras/GitHub/OpenIncidents/.github/workflows/release.yml) builds and publishes release assets for tags like `v1.0.0`

## Where Artifacts Are Uploaded

There are two upload targets:

- CI pushes and pull requests upload a temporary Actions artifact named `triage-ci-bundle` in the workflow run.
- Versioned releases upload downloadable assets to GitHub Releases for this repository:
  - [github.com/xperro/OpenIncidents/releases](https://github.com/xperro/OpenIncidents/releases)

To publish a real release, trigger [`.github/workflows/release.yml`](/Users/cristobalcontreras/GitHub/OpenIncidents/.github/workflows/release.yml) with a tag like `v1.0.0`, either by pushing the tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

or by running the workflow manually from GitHub Actions with the `tag` input.

## Download On macOS

Preferred release asset:

- `triage_<version>_bundle.tar.gz`

Browser flow:

1. Open [github.com/xperro/OpenIncidents/releases](https://github.com/xperro/OpenIncidents/releases)
2. Open the desired release tag
3. Download `triage_<version>_bundle.tar.gz`
4. Extract it and run:

```bash
tar -xzf triage_<version>_bundle.tar.gz
chmod +x triage
./triage --help
```

CLI flow with GitHub CLI:

```bash
gh release download v1.0.0 \
  --repo xperro/OpenIncidents \
  --pattern 'triage_1.0.0_bundle.tar.gz' \
  --dir ~/Downloads/openincidents
```

After extraction, you can run either:

- `./triage --help`
- `python3 triage.pyz --help`

## Download On Windows

Preferred release asset:

- `triage_<version>_bundle.zip`

Browser flow:

1. Open [github.com/xperro/OpenIncidents/releases](https://github.com/xperro/OpenIncidents/releases)
2. Open the desired release tag
3. Download `triage_<version>_bundle.zip`
4. Extract it and run:

```powershell
Expand-Archive -Path .\triage_<version>_bundle.zip -DestinationPath .\triage-bundle
cd .\triage-bundle
.\triage.cmd --help
py .\triage.pyz --help
```

CLI flow with GitHub CLI:

```powershell
gh release download v1.0.0 `
  --repo xperro/OpenIncidents `
  --pattern "triage_1.0.0_bundle.zip" `
  --dir "$env:USERPROFILE\\Downloads\\OpenIncidents"
```

## Download CI Artifact

If you only need the bundle from a regular push to `main` or `develop`, go to the workflow run in GitHub Actions and download the artifact named `triage-ci-bundle`.

That artifact is useful for internal validation, but the stable end-user download path should be the GitHub Releases page.

## Notes

- The CLI implementation target is Python and uses the standard library only.
- Product requirements, naming, and unresolved decisions still belong in `SPECS/triage/`, not in this README.
- If implementation and docs diverge, update the relevant spec instead of treating the README as canonical.
