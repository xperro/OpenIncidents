# Integration Specification: LLM Providers
Date: 2026-03-08

## Intent

Define the optional LLM analysis contract for OpenIncidents without making the core system dependent on one provider.

## Scope

- In scope:
  - provider selection
  - model selection
  - required result shape
  - payload safety expectations before provider submission
- Out of scope:
  - provider-specific prompt text
  - evaluation infrastructure
  - long-term storage of prompts or responses

## Responsibilities

- Define when LLM analysis is optional and how it fits into the pipeline.
- Keep provider selection separate from the stable core domain model.
- Define the required strict JSON output shape.
- Link to the canonical security rules for redaction and payload limits.

## Contracts

- Supported providers in the current plan:
  - `none`
  - `openai`
  - `anthropic`
- Model selection remains free-form and user-provided.
- Required result contract: `LLMResult`
  - `summary`
  - `suspected_cause`
  - `suggested_fix`
  - `confidence`
  - `safe_to_escalate`
- Safety constraints:
  - redact sensitive patterns before provider submission
  - cap payload size before sending any incident context
  - do not persist provider payloads by default in the MVP

## Dependencies

- Product baseline: [../00-product-overview.md](../00-product-overview.md)
- Architecture baseline: [../01-system-architecture.md](../01-system-architecture.md)
- Runtime contract: [../10-runtime/11-handler.md](../10-runtime/11-handler.md)
- Config contract: [30-config.md](30-config.md)
- Security baseline: [../40-governance/40-security-iam.md](../40-governance/40-security-iam.md)
- Open backlog: [../90-open-questions.md](../90-open-questions.md)

## Locked decisions

- LLM analysis is optional and never precedes reduction.
- OpenAI and Anthropic are the only named providers in the current MVP documentation.
- The provider and model are selected by the user rather than inferred automatically.
- The result must be strict JSON that can feed downstream notification logic.

## Open questions

- See [OQ-105](../90-open-questions.md#oq-105) for the exact mandatory redaction baseline.
- See [OQ-107](../90-open-questions.md#oq-107) for the secret-management threshold before production use.

## Deferred items

- Prompt versioning strategy
- Automatic quality evaluation and provider comparison
- Additional providers and fallback chains
