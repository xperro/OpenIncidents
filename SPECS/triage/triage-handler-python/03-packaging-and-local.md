# Python Receiver Service Packaging and Local Validation

## Intent

Describe how the Python implementation of `triage-handler` should run locally and be packaged as a serverless receiver service for GCP and AWS.

## Scope

- In scope:
  - local replay expectations
  - GCP packaging expectations
  - AWS packaging expectations
  - test strategy for the Python handler
- Out of scope:
  - Terraform definitions
  - container registry or IAM detail already covered elsewhere

## Responsibilities

- Define how the Python handler should be validated locally before deployment.
- Define how the cloud-specific Python variants differ at packaging time.
- Describe the artifact expectations handed off to `triage infra apply`.
- Describe the minimum test surface for Python-specific implementation work.

## Contracts

- Variant packaging model:
  - `triage-handler-python` ships as one GCP variant and one AWS variant
  - the canonical source trees are `triage/templates/python/gcp` and `triage/templates/python/aws`
  - the selected template contains only the cloud-specific entrypoints and packaging files required for that target
  - shared normalization, reduction, enrichment, notifier, and local replay modules remain structurally aligned across both variants
- Local validation:
  - support replay from `stdin` or file input
  - support optional local HTTP smoke validation by running the same `Starlette` app used for the Cloud Run path in the GCP variant
  - support local environment loading for untracked `.env`
  - support deterministic validation of normalization, enrichment, and outbound routing decisions
  - use standard-library helper entrypoints rather than third-party CLI frameworks for replay and utility commands
- GCP packaging:
  - package as a container image suitable for Cloud Run
  - expose the HTTP endpoint of the receiver service for Pub/Sub push delivery through the documented `Starlette` route layer
  - include a Python dependency manifest that pins the routing framework and any required ASGI runtime package for the container entrypoint
  - the current CLI packaging path materializes a Docker build context and publishes the image with `gcloud builds submit`
  - the generated build context must exclude local secret files such as `.env` and `.env.*` while preserving the checked-in `.env.example`
- AWS packaging:
  - package as a zip artifact suitable for Lambda
  - expose a Lambda-compatible receiver service entrypoint
  - bundle declared Python dependencies into the zip artifact so the Lambda package is self-contained at deploy time
- CLI handoff:
  - `triage infra apply` consumes the built artifact path or image reference produced from this implementation
- Minimum tests:
  - unit tests for normalization, thresholding, reduction, and repository enrichment
  - route tests for the `Starlette` HTTP surface, including the Pub/Sub ingress path and health endpoint
  - integration-style tests for Slack, Discord, and Jira clients using stub HTTP endpoints
  - adapter tests for GCP push payloads and AWS CloudWatch Logs events

## Dependencies

- Shared CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- GCP infra contract: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md)
- AWS infra contract: [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)

## Locked decisions

- Python handler packaging is split into one GCP variant and one AWS variant.
- Local replay remains part of the documented Python handler path.
- Cloud Run uses a container artifact and Lambda uses a zip artifact.
- Python local helper entrypoints stay within the standard library, while the deployed HTTP ingress may use the documented lightweight routing dependency set.

## Open questions

- See [../90-open-questions.md#oq-107](../90-open-questions.md#oq-107) for the hardening threshold for secret stores.

## Deferred items

- Performance profiling guidance
- Packaging optimization guidance beyond the baseline Cloud Run and Lambda paths
