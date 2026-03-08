# Integration Specification: Slack, Discord, and Jira
Date: 2026-03-08

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
- Keep Jira-related configuration easy to locate and change for operators.
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
  - issue type selected from `integrations.jira.issue_type`
  - reduced context and truncated stacktrace in the description
  - labels for `triage`, service, environment, and severity
- Integration enablement:
  - Slack, Discord, and Jira are individually configurable
  - Slack and Discord are the baseline outbound notification channels in the current design
  - Jira remains escalation-oriented rather than mandatory for every incident
- Jira creation policy:
  - a Jira ticket is created only when `integrations.jira.enabled` is `true`
  - a Jira ticket is created only when the reduced incident severity is greater than or equal to `policy.jira_min_severity`
  - the documented MVP default for `policy.jira_min_severity` is `CRITICAL`
  - the documented MVP default for `integrations.jira.issue_type` is `Bug`
  - if the project config omits `integrations.jira.issue_type`, the CLI must materialize the local `jira.issue_type_default` from `config.json`, defaulting that local value to `Bug` when absent
  - chat notifications to Slack and Discord still happen when their routing is enabled, even if a Jira ticket is also created
  - the runtime creates at most one Jira ticket per fingerprint within the current aggregation window
- Operator discovery path:
  - `triage config where integrations.jira.enabled`
  - `triage config where integrations.jira.issue_type`
  - `triage config where policy.jira_min_severity`
  - `triage config where jira.issue_type_default`
  - `triage config wizard`

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- Config operations guide: [33-config-operations.md](33-config-operations.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- Slack, Discord, and Jira are the named notification integrations in the current MVP documentation.
- Slack and Discord are the primary notification surfaces for actionable incidents.
- Jira ticket content must be derived from reduced incident context rather than raw unbounded logs.
- Jira escalation starts from severity `CRITICAL` in the documented MVP baseline.
- Jira issue type defaults to `Bug` unless the operator overrides it.
- Jira-related knobs must be discoverable from a single operator workflow.
- Notification structure is cloud-agnostic and should not branch by provider in this document.

## Open questions

- See [OQ-107](../90-open-questions.md#oq-107) for when cloud secret stores become the required deployment path.
- See [OQ-106](../90-open-questions.md#oq-106) for whether Jira escalation should expand beyond the baseline severity-only threshold.

## Deferred items

- Cross-channel deduplication across Slack and Discord posts
- Bidirectional Jira updates and richer ticket lifecycle automation
- Additional channels such as email or paging systems
