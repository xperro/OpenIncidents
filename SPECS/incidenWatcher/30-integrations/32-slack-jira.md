# Integration Specification: Slack and Discord
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the notification contracts that turn reduced incidents into actionable outputs.

## Scope

- In scope:
  - Slack message structure
  - Discord message structure
  - enablement rules and required configuration
  - relationship between incident data and outbound integrations
- Out of scope:
  - provider-specific authentication flows
  - UI-specific rendering beyond the documented fields

## Responsibilities

- Define the required fields that outbound integrations must receive.
- Keep notification rendering rules out of runtime and config documents.
- Describe the baseline relationship between Slack and Discord routing.
- Preserve consistent message structure across clouds.

## Contracts

- Slack message must include:
  - header with service, severity, and environment
  - short summary
  - occurrence count inside the aggregation window
  - source links when available
  - suggested fix when LLM analysis is enabled
- Discord message must include:
  - header with service, severity, and environment
  - short summary
  - occurrence count inside the aggregation window
  - source links when available
  - suggested fix when LLM analysis is enabled
- Integration enablement:
  - Slack and Discord are individually configurable
  - global routing in config supports `slack`, `discord`, or `both`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- Slack and Discord are the only named notification integrations in the current MVP documentation.
- Either Slack or Discord can be the primary channel through configuration.
- Notification structure is cloud-agnostic and should not branch by provider in this document.

## Open questions

- See [OQ-107](../90-open-questions.md#oq-107) for when cloud secret stores become the required deployment path.
- See [OQ-106](../90-open-questions.md#oq-106) for future service-level routing vs global routing only.
- See [OQ-111](../90-open-questions.md#oq-111) for Jira reintroduction policy.

## Deferred items

- Cross-channel deduplication across Slack and Discord posts
- Jira integration after the Slack/Discord MVP baseline
- Additional channels such as email or paging systems
