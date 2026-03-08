package local

import (
	"io"
	"os"

	"triage-handler/internal/runtime"
)

func ReadInput(path string) ([]byte, error) {
	if path == "-" {
		return io.ReadAll(os.Stdin)
	}
	return os.ReadFile(path)
}

func BuildReplaySummary(cloud string, entrypoint string, payload []byte) runtime.ReplaySummary {
	return runtime.NewReplaySummary(cloud, entrypoint, payload)
}
