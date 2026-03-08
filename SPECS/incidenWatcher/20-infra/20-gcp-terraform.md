# Infrastructure Specification: GCP Terraform
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the GCP deployment contract for routing Cloud Logging events into the OpenIncidents runtime.

## Scope

- In scope:
  - log export from Cloud Logging
  - Pub/Sub transport
  - Cloud Run deployment target for `triage-handler`
  - Terraform inputs and outputs required by the CLI and runtime
- Out of scope:
  - full IAM policy duplication
  - multi-project aggregation
  - BigQuery exports

## Responsibilities

- Describe the minimum GCP resources required by the MVP path.
- Define the Terraform variables and outputs that other components depend on.
- State the default log filter shape for the GCP path.
- Link back to the canonical IAM and security policy instead of repeating it.

## Contracts

- MVP resource set:
  - Pub/Sub topic
  - Pub/Sub subscription
  - Cloud Logging sink targeting the topic
  - Cloud Run service for `triage-handler`
- Default log filter:
  - preferred default: `severity>=WARNING`
  - explicit-level variant may be documented as an alternative
- Core Terraform inputs:
  - `project_id`
  - `region`
  - `env`
  - `sink_name`
  - `log_filter`
  - `topic_name`
  - `subscription_name`
  - `cloud_run_service_name`
  - `container_image`
- Core Terraform outputs:
  - `pubsub_topic`
  - `pubsub_subscription`
  - `sink_writer_identity`
  - `cloud_run_url`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Security and IAM: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- The GCP path is documented as Cloud Logging sink to Pub/Sub to Cloud Run.
- GCP is the first implementation target for the MVP delivery sequence.
- The sink writer identity must be surfaced as an output because downstream permissions depend on it.
- Secret handling stays at the environment-variable level for the current MVP documentation, with stronger secret-store guidance tracked separately.
- GCP resource detail belongs here, not in runtime or governance documents.

## Open questions

- See [OQ-102](../90-open-questions.md#oq-102) for the preferred runtime delivery model on GCP.
- See [OQ-107](../90-open-questions.md#oq-107) for when Secret Manager should become mandatory.

## Deferred items

- Secret Manager integration as the default path
- Multi-project aggregation
- Additional export targets such as BigQuery
