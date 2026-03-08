# Integration Specification: Slack and Jira
Date: 2026-03-08

## Intent

Define the notification and ticketing contracts that turn reduced incidents into actionable outputs.

## Scope

- In scope:
  - Slack message structure
  - Jira ticket structure
  - enablement rules and required configuration
  - relationship between incident data and outbound integrations
- Out of scope:
  - provider-specific authentication flows
  - ticket lifecycle automation after creation
  - UI-specific rendering beyond the documented fields

## Responsibilities

- Define the required fields that outbound integrations must receive.
- Keep notification rendering rules out of runtime and config documents.
- Describe the baseline relationship between Slack visibility and Jira escalation.
- Preserve consistent message and ticket structure across clouds.

## Contracts

- Slack message must include:
  - header with service, severity, and environment
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
  - Slack and Jira are individually configurable
  - Slack is the baseline outbound notification channel in the current design

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- Slack and Jira are the only named notification integrations in the current MVP documentation.
- Slack remains the primary notification surface for actionable incidents.
- Jira ticket content must be derived from reduced incident context rather than raw unbounded logs.
- Notification structure is cloud-agnostic and should not branch by provider in this document.

## Open questions

- See [OQ-106](../90-open-questions.md#oq-106) for the exact ticket-creation threshold.
- See [OQ-107](../90-open-questions.md#oq-107) for when cloud secret stores become the required deployment path.

## Deferred items

- Bidirectional Jira updates
- Issue deduplication across multiple incidents
- Additional channels such as email or paging systems
