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
  - Artifact Registry image storage for handler deployment
  - service accounts and IAM bindings required by the documented path
  - Terraform inputs and outputs required by the CLI and runtime
- Out of scope:
  - full IAM policy duplication
  - multi-project aggregation
  - BigQuery exports

## Responsibilities

- Describe the minimum GCP resources required by the MVP path.
- Define the Terraform variables and outputs that other components depend on.
- State the default log filter shape for the GCP path.
- Define the documented handoff between `triage` packaging and Terraform apply.
- Link back to the canonical IAM and security policy instead of repeating it.

## Contracts

- MVP resource set:
  - Artifact Registry repository
  - Cloud Run service account
  - Cloud Run service for `triage-handler`
  - Pub/Sub topic
  - Pub/Sub push subscription
  - Cloud Logging sink targeting the topic
  - IAM bindings for the sink writer and Pub/Sub push delivery path
- Default log filter:
  - `severity_min` maps to a Cloud Logging filter in the form `severity>=X`
  - supported threshold values are `DEBUG`, `INFO`, `NOTICE`, `WARNING`, `ERROR`, `CRITICAL`, `ALERT`, and `EMERGENCY`
  - `log_filter_override` replaces the derived filter when explicitly set
  - severity semantics follow the official [Google Cloud LogSeverity reference](https://cloud.google.com/logging/docs/reference/v2/rpc/google.logging.type#logseverity)
- CLI workflow contract:
  - `triage` builds the selected handler from an absolute local path
  - `triage` publishes the resulting image to Artifact Registry
  - `triage` passes the resolved `container_image` into Terraform before `infra apply`
- Core Terraform inputs:
  - `project_id`
  - `region`
  - `env`
  - `sink_name`
  - `log_filter`
  - `topic_name`
  - `subscription_name`
  - `cloud_run_service_name`
  - `artifact_registry_repository`
  - `container_image`
- Core Terraform outputs:
  - `pubsub_topic`
  - `pubsub_subscription`
  - `sink_writer_identity`
  - `cloud_run_url`
  - `artifact_registry_repository`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- CLI contract: [../10-runtime/10-cli.md](../10-runtime/10-cli.md)
- Security and IAM: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- The GCP path is documented as Cloud Logging sink to Pub/Sub to Cloud Run.
- Pub/Sub delivery into Cloud Run is push-based in the canonical design.
- The sink writer identity must be surfaced as an output because downstream permissions depend on it.
- GCP filter derivation starts from `policy.severity_min` unless `log_filter_override` is set.
- Secret handling stays at the environment-variable level for the current MVP documentation, with stronger secret-store guidance tracked separately.
- GCP resource detail belongs here, not in runtime or governance documents.

## Open questions

- See [OQ-107](../90-open-questions.md#oq-107) for when Secret Manager should become mandatory.

## Deferred items

- Secret Manager integration as the default path
- Multi-project aggregation
- Additional export targets such as BigQuery
