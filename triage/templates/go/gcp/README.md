# triage-handler (go, gcp)

Go GCP handler template for `triage-handler`.

- Required local Go version: 1.26.1
- `go.mod` intentionally omits a `toolchain` directive; install Go 1.26.1 locally before running or packaging this template
- Runtime shape: Cloud Run receiver service plus local replay entrypoint
- Source layout: `cmd/triage-handler`, `cmd/triage-handler-local`, `internal/`, `sample-events/`
- The placeholder replay/output contract preserves the decoded Cloud Logging payload as `logging_event` and adds derived fields such as `repo_name`, `sink_name`, and `error_message` when they can be inferred
