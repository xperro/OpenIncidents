package runtime

type ReplaySummary struct {
	Handler       string `json:"handler"`
	Runtime       string `json:"runtime"`
	Cloud         string `json:"cloud"`
	Entrypoint    string `json:"entrypoint"`
	PayloadLength int    `json:"payload_length"`
	RepoName      string `json:"repo_name,omitempty"`
	SinkName      string `json:"sink_name,omitempty"`
	ErrorMessage  string `json:"error_message,omitempty"`
	LoggingEvent  map[string]any `json:"logging_event,omitempty"`
}

func NewReplaySummary(cloud string, entrypoint string, payload []byte, repoName string, sinkName string) ReplaySummary {
	summary := ReplaySummary{
		Handler:       "triage-handler",
		Runtime:       "go",
		Cloud:         cloud,
		Entrypoint:    entrypoint,
		PayloadLength: len(payload),
	}
	logEntry := decodeGCPPubSubLogEntry(payload)
	if len(logEntry) > 0 {
		summary.LoggingEvent = logEntry
	}
	summary.RepoName, summary.SinkName = classifyGCPLogEntry(logEntry, repoName, sinkName)
	summary.ErrorMessage = extractClearError(logEntry)
	return summary
}
