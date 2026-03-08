# triage-handler (go, aws)

Go AWS handler template for `triage-handler`.

- Required local Go version: 1.26.1
- `go.mod` intentionally omits a `toolchain` directive; install Go 1.26.1 locally before running or packaging this template
- Runtime shape: Lambda receiver service plus local replay entrypoint
- Source layout: `cmd/triage-handler-lambda`, `cmd/triage-handler-local`, `internal/`, `sample-events/`
