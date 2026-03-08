package runtime

type ReplaySummary struct {
	Handler       string `json:"handler"`
	Runtime       string `json:"runtime"`
	Cloud         string `json:"cloud"`
	Entrypoint    string `json:"entrypoint"`
	PayloadLength int    `json:"payload_length"`
}

func NewReplaySummary(cloud string, entrypoint string, payload []byte) ReplaySummary {
	return ReplaySummary{
		Handler:       "triage-handler",
		Runtime:       "go",
		Cloud:         cloud,
		Entrypoint:    entrypoint,
		PayloadLength: len(payload),
	}
}
