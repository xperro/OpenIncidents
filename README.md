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
  - end-to-end LLM commands: `llm-prep`, `llm-request`, `llm-client`, `llm-resolve`
  - notifier command: `notify` (Discord, Slack, Jira)
  - end-to-end scan command: `scan`
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

- `triage help [command ...]`
- `triage h [command ...]`
- `triage init`
- `triage llm-prep`
- `triage llm-request`
- `triage llm-client`
- `triage llm-resolve`
- `triage notify`
- `triage scan`
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

### 1. Run the CLI locally from the repository

```bash
python3 -m triage --help
python3 -m triage help infra apply
```

You can also ask for contextual help on command groups:

```bash
python3 -m triage settings
python3 -m triage infra
```

### 2. Run the test suite locally

```bash
.venv/bin/python -m pytest -q
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

For the GCP path, the scaffold now derives default resource names from `env`:

- `gcp.sink_name`: `triage-<env>`
- `gcp.topic_name`: `triage-<env>`
- `gcp.subscription_name`: `triage-<env>-push`
- `gcp.sinks`: optional preferred list for multi-sink routing; sinks share the project topic/subscription, prefer inclusion-first filters (`filter` + `include_*`), and carry repo-routing metadata into the handler runtime

Example:

- `env: dev` => `triage-dev`, `triage-dev`, `triage-dev-push`
- `gcp.sinks[].name: approve-mrs-dev` => dedicated sink name, shared topic `triage-dev`, shared subscription `triage-dev-push`

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

For GCP, `triage infra apply` now:

- bootstraps Artifact Registry through Terraform
- builds and publishes the selected handler as a container image with `gcloud builds submit`
- runs the final Terraform apply against Cloud Run, a shared Pub/Sub push path, and Cloud Logging sink resources
- injects sink routing metadata into Cloud Run so the handler can recover `repo_name`, `sink_name`, a clearer `error_message`, and the decoded `logging_event` from the pushed log event

### 5. Smoke test a handler locally

For a pure local replay, disable external notifiers you do not want to call yet in `triage.yaml` or point them at test credentials and endpoints first.

Python example with a bundled sample event:

```bash
python3 -m triage run \
  --cloud gcp \
  --runtime python \
  --handler-path /absolute/path/to/triage-handler \
  --input /absolute/path/to/triage-handler/sample-events/gcp-pubsub.json
```

The same replay can be piped on stdin:

```bash
cat /absolute/path/to/triage-handler/sample-events/gcp-pubsub.json | \
  python3 -m triage run \
    --cloud gcp \
    --runtime python \
    --handler-path /absolute/path/to/triage-handler
```

Go local replay uses the same `triage run` command shape, but the downloaded Go GCP template expects Go `1.26.1` locally.

For GCP, the placeholder handler replay now returns the decoded `logging_event` plus enriched fields such as `repo_name`, `sink_name`, and `error_message`.

### 6. Build release assets locally

```bash
python3 scripts/build_release.py --output-dir dist/local
```

This produces:

- `triage.pyz`
- `triage`
- `triage.cmd`
- versioned `.tar.gz` and `.zip` bundles
- SHA256 checksum output

### 7. Run End-To-End Scan

With `.env` configured:

```bash
python3 -m triage scan --output "$(pwd)/scan-result.json"
```

Artifacts are written to `.triage/build/local/scan/`:

- `prepared.json`
- `llm-request.json`
- `llm-analysis.json`
- `llm-notify.json` (when notify is enabled)

If repository context cannot be loaded (clone/update/auth failure), scan continues and reports:

- `meta.repo_context_enabled`
- `meta.repo_context_error`

## CI And Release

- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs:
  - unit tests on Ubuntu, macOS, and Windows
  - a CLI smoke test with `python -m triage --help`
  - release bundle build and extraction checks
- [`.github/workflows/release.yml`](.github/workflows/release.yml) builds and publishes release assets for tags like `v1.0.8`

## Where Artifacts Are Uploaded

There are two upload targets:

- CI pushes and pull requests upload a temporary Actions artifact named `triage-ci-bundle` in the workflow run.
- Versioned releases upload downloadable assets to GitHub Releases for this repository:
  - [github.com/xperro/OpenIncidents/releases](https://github.com/xperro/OpenIncidents/releases)

To publish a real release, trigger [`.github/workflows/release.yml`](.github/workflows/release.yml) with a tag like `v1.0.8`, either by pushing the tag:

```bash
git tag v1.0.8
git push origin v1.0.8
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
gh release download v1.0.8 \
  --repo xperro/OpenIncidents \
  --pattern 'triage_1.0.8_bundle.tar.gz' \
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
gh release download v1.0.8 `
  --repo xperro/OpenIncidents `
  --pattern "triage_1.0.8_bundle.zip" `
  --dir "$env:USERPROFILE\\Downloads\\OpenIncidents"
```

## Download CI Artifact

If you only need the bundle from a regular push to `main` or `develop`, go to the workflow run in GitHub Actions and download the artifact named `triage-ci-bundle`.

That artifact is useful for internal validation, but the stable end-user download path should be the GitHub Releases page.

## Notes

- The CLI implementation target is Python and uses the standard library only.
- Product requirements, naming, and unresolved decisions still belong in `SPECS/triage/`, not in this README.
- If implementation and docs diverge, update the relevant spec instead of treating the README as canonical.
