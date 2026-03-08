# Triage Handler Service Model

## Related specs

- [../../SPECS/triage/01-system-architecture.md](../../SPECS/triage/01-system-architecture.md)
- [../../SPECS/triage/10-runtime/11-handler.md](../../SPECS/triage/10-runtime/11-handler.md)
- [../../SPECS/triage/20-infra/20-gcp-terraform.md](../../SPECS/triage/20-infra/20-gcp-terraform.md)
- [../../SPECS/triage/20-infra/21-aws-terraform.md](../../SPECS/triage/20-infra/21-aws-terraform.md)

## AGENTS constraints used

- Keep `triage` as the canonical CLI name.
- Keep `triage-handler` as the canonical runtime name.
- Clarify product contracts in `SPECS/triage/` before implementation.
- Use `.codex` only as working context, not as canonical product documentation.

## Decisions captured

- `triage-handler` is documented as a serverless receiver service, not just as an internal callback.
- On GCP, the receiver service is exposed through a Cloud Run HTTP endpoint reached by Pub/Sub push delivery.
- On AWS, the receiver service is exposed through a Lambda entrypoint invoked by the log subscription path.
- The stable runtime name remains `triage-handler` even though the implementation is described as a service.

## Open questions still relevant

- [OQ-104](../../SPECS/triage/90-open-questions.md#oq-104)
- [OQ-106](../../SPECS/triage/90-open-questions.md#oq-106)
- [OQ-107](../../SPECS/triage/90-open-questions.md#oq-107)

## Follow-up

- Keep future runtime and infra wording aligned with the receiver service model.
- Add concrete cloud event envelope examples once code templates exist.
