# Runtime Specification: CLI Release Automation
Date: 2026-03-08

## Intent

Define the canonical CI and release automation path for publishing the `triage` CLI through GitHub Actions.

## Scope

- In scope:
  - GitHub Actions CI validation for the CLI
  - release-time packaging of the Python CLI into a portable bundle
  - GitHub Release asset publication
  - Homebrew publication for macOS through a configured tap repository
  - post-release smoke validation of published assets
- Out of scope:
  - package manager publication such as `pip`, Scoop, or `pipx`
  - cloud deployment workflows for generated projects
  - handler runtime release automation

## Responsibilities

- Define the official automation path for validating the CLI on pull requests and protected branches.
- Define how the release bundle is built from the repository contents.
- Define which assets a GitHub Release must publish for the CLI.
- Define the minimal smoke checks that must run before and after publication.

## Contracts

- Automation platform:
  - GitHub Actions is the canonical CI and release automation platform for the CLI
  - repository workflows live under `.github/workflows/`
- CI workflow contract:
  - a `ci` workflow validates the CLI on `push` and `pull_request`
  - the CI matrix must run on `ubuntu-latest`, `macos-latest`, and `windows-latest`
  - the CI matrix must run on the supported CPython versions for the CLI release line, starting with Python `3.13` and `3.14`
  - CI may provision Go when the CLI test suite exercises official Go handler template flows
  - CI must run the repository test suite and a help smoke test for the CLI entrypoint
  - CI may build a release bundle as a non-publishing verification step
- Release trigger contract:
  - a `release` workflow publishes the CLI on pushed Git tags matching `v*`
  - the same workflow may support `workflow_dispatch` with an explicit tag input for manual recovery or reruns
- Packaging contract:
  - release packaging uses Python standard-library tooling only
  - the canonical executable asset is `triage.pyz`
  - `triage.pyz` is built as a zipapp from the repository CLI source tree and must embed `triage/templates/`
  - the release bundle also contains a Unix launcher named `triage`
  - the release bundle also contains a Windows launcher named `triage.cmd`
  - the launcher scripts remain thin wrappers that delegate to the colocated `triage.pyz`
  - release archives do not need a second external template tree as long as `triage.pyz` embeds `triage/templates/`, so `triage template download` works without network access
  - release archives must exclude junk and build byproducts such as `__pycache__`, `.pytest_cache`, `.DS_Store`, `.git`, and `*.pyc`
- Published asset contract:
  - a GitHub Release must publish `triage.pyz`
  - a GitHub Release must publish `triage`
  - a GitHub Release must publish `triage.cmd`
  - a GitHub Release must publish a Unix-friendly archive named `triage_<version>_bundle.tar.gz`
  - a GitHub Release must publish a Windows-friendly archive named `triage_<version>_bundle.zip`
  - a GitHub Release must publish a checksum manifest named `triage_<version>_sha256sums.txt`
  - a GitHub Release must publish a Homebrew formula asset named `triage_<version>_homebrew.rb`
- Homebrew publication contract:
  - macOS distribution may additionally be published through a Homebrew tap
  - the release build must generate a formula that installs `triage.pyz` and exposes a `triage` launcher through Homebrew
  - the formula must reference the tagged GitHub Release tarball and its SHA-256 digest
  - GitHub Actions may publish the formula to a tap repository only when the tap repository and token are configured explicitly
  - the canonical workflow inputs are a repository variable named `HOMEBREW_TAP_REPOSITORY` and a secret named `HOMEBREW_TAP_TOKEN`
  - the canonical tap target path is `Formula/triage.rb`
- Version contract:
  - the Git tag version and the CLI version embedded in the source must match for an official release
  - release automation must fail fast when the source version and tag disagree
- Post-release validation contract:
  - after publishing, the workflow must download the published assets on Linux, macOS, and Windows
  - Linux and macOS validation must prove that the extracted launcher can execute `triage --help`
  - Windows validation must prove that either `triage.cmd --help` or `py triage.pyz --help` succeeds from the extracted bundle
- Permissions contract:
  - the release workflow needs GitHub `contents: write` permission to create or update GitHub Release assets
  - package registry publication is not part of the MVP release path

## Dependencies

- CLI contract: [10-cli.md](10-cli.md)
- CLI local state contract: [12-cli-state.md](12-cli-state.md)
- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- GitHub Actions is the canonical automation path for releasing `triage`.
- The official release artifact remains a portable `pyz` bundle rather than a wheel or package-manager-specific build.
- Release automation validates published assets across Linux, macOS, and Windows even though the build itself may run on a single platform.
- GitHub Releases are the canonical publication surface for the CLI in the current phase.

## Open questions

- None at this time.

## Deferred items

- Scoop or `pipx` installation channels
- Signed release assets
- Automated changelog generation
