# Go Receiver Service Packaging and Local Validation

## Intent

Describe how the Go implementation of `triage-handler` should run locally and be packaged as a serverless receiver service for GCP and AWS.

## Scope

- In scope:
  - local replay expectations
  - GCP packaging expectations
  - AWS packaging expectations
  - test strategy for the Go handler
- Out of scope:
  - Terraform definitions
  - container registry or IAM detail already covered elsewhere

## Responsibilities

- Define how the Go handler should be validated locally before deployment.
- Define how the cloud-specific Go variants differ at packaging time.
- Describe the artifact expectations handed off to `triage infra apply`.
- Describe the minimum test surface for Go-specific implementation work.

## Contracts

- Variant packaging model:
  - `triage-handler-go` ships as one GCP variant and one AWS variant
  - the canonical source trees are `triage/templates/go/gcp` and `triage/templates/go/aws`
  - the selected template contains only the cloud-specific entrypoints and packaging files required for that target
  - shared normalization, reduction, enrichment, notifier, and local replay packages remain structurally aligned across both variants
- Local validation:
  - support replay from `stdin` or file input
  - support optional local HTTP smoke validation by running the same `chi` router used for the Cloud Run path in the GCP variant
  - support local environment loading for untracked `.env`
  - support deterministic validation of normalization, enrichment, and outbound routing decisions
- GCP packaging:
  - package as a container image suitable for Cloud Run
  - expose the HTTP endpoint of the receiver service for Pub/Sub push delivery through the documented `chi` route layer
  - include `go.mod` and `go.sum` that pin the routing framework and any runtime-specific module dependencies
- AWS packaging:
  - package as a zip artifact suitable for Lambda
  - expose a Lambda-compatible receiver service entrypoint
  - compile the Lambda artifact from the documented Go module so the zip contains a self-contained binary built from the pinned dependencies
- CLI handoff:
  - `triage infra apply` consumes the built artifact path or image reference produced from this implementation
- Minimum tests:
  - unit tests for normalization, thresholding, reduction, and repository enrichment
  - route tests for the `chi` HTTP surface, including the Pub/Sub ingress path and health endpoint
  - integration-style tests for Slack, Discord, and Jira clients using stub servers
  - adapter tests for GCP push payloads and AWS CloudWatch Logs events

## Dependencies

- Shared CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- GCP infra contract: [../20-infra/20-gcp-terraform.md](../20-infra/20-gcp-terraform.md)
- AWS infra contract: [../20-infra/21-aws-terraform.md](../20-infra/21-aws-terraform.md)

## Locked decisions

- Go handler packaging is split into one GCP variant and one AWS variant.
- Local replay remains part of the documented Go handler path.
- Cloud Run uses a container artifact and Lambda uses a zip artifact.
- Packaging detail here must stay compatible with the shared CLI contract and the documented Go module layout.

## Open questions

- See [../90-open-questions.md#oq-107](../90-open-questions.md#oq-107) for the hardening threshold for secret stores.

## Deferred items

- Performance benchmarking guidance
- Multi-architecture build guidance beyond the baseline packaging path
