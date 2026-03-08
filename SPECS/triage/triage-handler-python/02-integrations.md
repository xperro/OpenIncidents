# Python Receiver Service Integrations

## Intent

Describe how the Python implementation of `triage-handler` as a receiver service should integrate with Slack, Discord, and Jira.

## Scope

- In scope:
  - outbound HTTP behavior
  - required environment-backed credentials
  - error handling, retry posture, and timeouts
  - mapping from reduced incidents into outbound calls
- Out of scope:
  - redefining Slack, Discord, or Jira payload semantics
  - introducing third-party client or CLI frameworks

## Responsibilities

- Define Python-specific outbound integration behavior without changing the shared payload contract.
- Keep notifier code isolated from normalization and reduction logic.
- Document failure handling that preserves receiver service observability.

## Contracts

- Standard-library baseline:
  - local helper entrypoints use `argparse`
  - HTTP calls use Python standard-library networking modules such as `urllib.request` or `http.client`
  - JSON payload handling uses the standard library
  - third-party CLI frameworks are not allowed
- Slack:
  - uses `integrations.slack.webhook_env`
  - sends the shared incident payload fields required by [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Discord:
  - uses `integrations.discord.webhook_env`
  - mirrors the shared incident payload contract used for chat notifications
- Jira:
  - uses `integrations.jira.base_url`, `project_key`, `email_env`, and `token_env`
  - creates tickets only when policy allows escalation
- Failure handling:
  - network or remote API failures must be logged with request correlation and integration target
  - chat delivery failures must not corrupt incident normalization or reduction
  - Jira failures must not suppress Slack or Discord delivery
- Retry posture:
  - no unbounded retries inside a single request path
  - allow small bounded retries only for transient outbound failures
- Timeouts:
  - outbound timeouts must be explicit and shorter than the surrounding runtime request budget

## Dependencies

- Shared runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Notification contract: [../30-integrations/32-slack-jira.md](../30-integrations/32-slack-jira.md)
- Config contract: [../30-integrations/30-config.md](../30-integrations/30-config.md)

## Locked decisions

- Python integration code uses standard-library modules for HTTP and JSON handling.
- Slack, Discord, and Jira are all first-class outbound integrations for the Python handler.
- Integration-specific failures are isolated and observable.

## Open questions

- See [../90-open-questions.md#oq-106](../90-open-questions.md#oq-106) for whether Jira escalation should expand beyond the baseline severity threshold.

## Deferred items

- Richer retry policies beyond small bounded retries
- Additional outbound integrations beyond Slack, Discord, and Jira
