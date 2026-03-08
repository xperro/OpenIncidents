package gcp

import (
	"encoding/json"
	"io"
	"net/http"

	"triage-handler/internal/runtime"
)

func HandlePush(writer http.ResponseWriter, request *http.Request) {
	payload, err := io.ReadAll(request.Body)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusBadRequest)
		return
	}

	writer.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(writer).Encode(runtime.NewReplaySummary("gcp", "cloud-run-http", payload))
}

func Healthz(writer http.ResponseWriter, _ *http.Request) {
	writer.Header().Set("Content-Type", "application/json")
	_, _ = writer.Write([]byte(`{"status":"ok"}`))
}
