# Integration Specification: Slack, Discord, and Jira
Date: 2026-03-08
Authors: Jorge Aguilera (xperro) / Cristobal Contreras (chrisloarryn)

## Intent

Define the notification and ticketing contracts that turn reduced incidents into actionable outputs.

## Scope

- In scope:
  - Slack message structure
  - Discord message structure
  - Jira ticket structure
  - enablement rules and required configuration
  - relationship between incident data and outbound integrations
- Out of scope:
  - provider-specific authentication flows
  - UI-specific rendering beyond the documented fields

## Responsibilities

- Define the required fields that outbound integrations must receive.
- Keep notification rendering rules out of runtime and config documents.
- Describe the baseline relationship between chat visibility and Jira escalation.
- Preserve consistent message and ticket structure across clouds.

## Contracts

- Slack message must include:
  - header with service, severity, and environment
  - short summary
  - occurrence count inside the aggregation window
  - source links when available
  - suggested fix when LLM analysis is enabled
- Discord message must include the same incident facts required by Slack:
  - service, severity, and environment
  - short summary
  - occurrence count inside the aggregation window
  - source links when available
  - Jira link when a ticket exists
  - suggested fix when LLM analysis is enabled
- Jira ticket must include:
  - summary using environment, service, and severity
  - reduced context and truncated stacktrace in the description
  - labels for `triage`, service, environment, and severity
- Integration enablement:
  - Slack, Discord, and Jira are individually configurable
  - Slack and Discord are the baseline outbound notification channels in the current design
  - Jira remains escalation-oriented rather than mandatory for every incident

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- Slack, Discord, and Jira are the named notification integrations in the current MVP documentation.
- Slack and Discord are the primary notification surfaces for actionable incidents.
- Jira ticket content must be derived from reduced incident context rather than raw unbounded logs.
- Notification structure is cloud-agnostic and should not branch by provider in this document.

## Open questions

- See [OQ-107](../90-open-questions.md#oq-107) for when cloud secret stores become the required deployment path.
- See [OQ-106](../90-open-questions.md#oq-106) for the exact Jira ticket-creation threshold relative to Slack and Discord notifications.

## Deferred items

- Cross-channel deduplication across Slack and Discord posts
- Bidirectional Jira updates and richer ticket lifecycle automation
- Additional channels such as email or paging systems
