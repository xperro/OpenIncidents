# Triage CLI Implementation

## Related specs

- [../../SPECS/triage/README.md](../../SPECS/triage/README.md)
- [../../SPECS/triage/00-product-overview.md](../../SPECS/triage/00-product-overview.md)
- [../../SPECS/triage/01-system-architecture.md](../../SPECS/triage/01-system-architecture.md)
- [../../SPECS/triage/10-runtime/10-cli.md](../../SPECS/triage/10-runtime/10-cli.md)
- [../../SPECS/triage/10-runtime/11-handler.md](../../SPECS/triage/10-runtime/11-handler.md)
- [../../SPECS/triage/10-runtime/12-cli-state.md](../../SPECS/triage/10-runtime/12-cli-state.md)
- [../../SPECS/triage/20-infra/20-gcp-terraform.md](../../SPECS/triage/20-infra/20-gcp-terraform.md)
- [../../SPECS/triage/20-infra/21-aws-terraform.md](../../SPECS/triage/20-infra/21-aws-terraform.md)
- [../../SPECS/triage/30-integrations/30-config.md](../../SPECS/triage/30-integrations/30-config.md)
- [../../SPECS/triage/30-integrations/33-config-operations.md](../../SPECS/triage/30-integrations/33-config-operations.md)

## AGENTS constraints used

- `AGENTS.md` remains the repository source of truth.
- The work stays limited to the CLI in this thread.
- Naming remains fixed as `OpenIncidents`, `triage`, and `triage-handler`.
- The implementation follows the documentation-first contracts instead of inventing alternative names or flows.

## Decisions applied in code

- The first implementation target is a Python package runnable as `python -m triage`.
- The CLI uses only standard-library modules and `argparse`.
- `triage.yaml` is handled through a small YAML subset parser/writer matching the documented canonical shape.
- Bootstrap gating, local CLI state, config discovery, template extraction, infra scaffold generation, and local replay are implemented inside the CLI layer.
- `infra generate|plan|apply` currently produce deterministic Terraform scaffolds and packaging handoff metadata suitable for expanding into real cloud resources later.

## Follow-up

- Replace placeholder Terraform outputs with real provider resources when the infrastructure implementation starts.
- Replace placeholder handler templates with real Go and Python `triage-handler` implementations when those threads begin.
