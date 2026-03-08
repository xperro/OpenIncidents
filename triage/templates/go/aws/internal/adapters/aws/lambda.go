package aws

import (
	"context"
	"encoding/json"

	"triage-handler/internal/runtime"
)

func Handle(_ context.Context, event map[string]any) (map[string]any, error) {
	payload, err := json.Marshal(event)
	if err != nil {
		return nil, err
	}
	summary := runtime.NewReplaySummary("aws", "lambda", payload)
	return map[string]any{
		"handler":        summary.Handler,
		"runtime":        summary.Runtime,
		"cloud":          summary.Cloud,
		"entrypoint":     summary.Entrypoint,
		"payload_length": summary.PayloadLength,
	}, nil
}
