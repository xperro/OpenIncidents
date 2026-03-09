package runtime

import (
	"encoding/base64"
	"encoding/json"
	"os"
	"regexp"
	"strings"
)

const routingEnv = "TRIAGE_GCP_SINK_ROUTING"

var bitbucketRepoPattern = regexp.MustCompile(`bitbucket\.org/[^/]+/([^/]+)/pull-requests/\d+`)

type pubSubEnvelope struct {
	Message struct {
		Data string `json:"data"`
	} `json:"message"`
}

type routingEntry struct {
	SinkName      string `json:"sink_name"`
	RepoName      string `json:"repo_name"`
	RepoMatchLike string `json:"repo_match_like"`
}

func decodeGCPPubSubLogEntry(payload []byte) map[string]any {
	var envelope pubSubEnvelope
	if err := json.Unmarshal(payload, &envelope); err != nil {
		return map[string]any{}
	}
	if strings.TrimSpace(envelope.Message.Data) == "" {
		return map[string]any{}
	}
	decoded, err := base64.StdEncoding.DecodeString(envelope.Message.Data)
	if err != nil {
		return map[string]any{}
	}
	var logEntry map[string]any
	if err := json.Unmarshal(decoded, &logEntry); err != nil {
		return map[string]any{}
	}
	return logEntry
}

func classifyGCPLogEntry(logEntry map[string]any, repoName string, sinkName string) (string, string) {
	if repoName != "" || sinkName != "" {
		return repoName, sinkName
	}
	searchable := collectSearchableFields(logEntry)
	for _, route := range loadGCPRouting() {
		needle := strings.ToLower(strings.TrimSpace(route.RepoMatchLike))
		if needle == "" {
			continue
		}
		for _, candidate := range searchable {
			if strings.Contains(candidate, needle) {
				return strings.TrimSpace(route.RepoName), strings.TrimSpace(route.SinkName)
			}
		}
	}
	return inferRepoName(logEntry), ""
}

func loadGCPRouting() []routingEntry {
	raw := strings.TrimSpace(os.Getenv(routingEnv))
	if raw == "" {
		return nil
	}
	var entries []routingEntry
	if err := json.Unmarshal([]byte(raw), &entries); err != nil {
		return nil
	}
	return entries
}

func collectSearchableFields(logEntry map[string]any) []string {
	fields := []string{
		asString(logEntry["logName"]),
		asString(logEntry["textPayload"]),
		nestedString(logEntry, "jsonPayload", "message"),
		nestedString(logEntry, "jsonPayload", "repo_name"),
		nestedString(logEntry, "jsonPayload", "repository"),
		nestedString(logEntry, "labels", "run.googleapis.com/service_name"),
		nestedString(logEntry, "resource", "labels", "service_name"),
		nestedString(logEntry, "resource", "labels", "revision_name"),
		nestedString(logEntry, "protoPayload", "resourceName"),
		nestedString(logEntry, "protoPayload", "authenticationInfo", "principalEmail"),
	}
	var resolved []string
	for _, field := range fields {
		if strings.TrimSpace(field) != "" {
			resolved = append(resolved, strings.ToLower(strings.TrimSpace(field)))
		}
	}
	return resolved
}

func inferRepoName(logEntry map[string]any) string {
	for _, candidate := range []string{
		nestedString(logEntry, "resource", "labels", "service_name"),
		nestedString(logEntry, "labels", "run.googleapis.com/service_name"),
		nestedString(logEntry, "jsonPayload", "repo_name"),
		nestedString(logEntry, "jsonPayload", "repository"),
	} {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	match := bitbucketRepoPattern.FindStringSubmatch(asString(logEntry["textPayload"]))
	if len(match) == 2 {
		return match[1]
	}
	return ""
}

func extractClearError(logEntry map[string]any) string {
	if textPayload := asString(logEntry["textPayload"]); strings.TrimSpace(textPayload) != "" {
		return strings.TrimSpace(textPayload)
	}
	if found := findMessage(logEntry["jsonPayload"]); found != "" {
		return found
	}
	if found := findMessage(logEntry["protoPayload"]); found != "" {
		return found
	}
	methodName := nestedString(logEntry, "protoPayload", "methodName")
	resourceName := nestedString(logEntry, "protoPayload", "resourceName")
	return strings.TrimSpace(strings.TrimSpace(methodName + " " + resourceName))
}

func findMessage(value any) string {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	case []any:
		for _, item := range typed {
			if found := findMessage(item); found != "" {
				return found
			}
		}
	case map[string]any:
		for _, key := range []string{"message", "summary", "error", "err", "exception", "detail", "details"} {
			if found := findMessage(typed[key]); found != "" {
				return found
			}
		}
		for _, item := range typed {
			if found := findMessage(item); found != "" {
				return found
			}
		}
	}
	return ""
}

func nestedString(root map[string]any, path ...string) string {
	var current any = root
	for _, key := range path {
		next, ok := current.(map[string]any)
		if !ok {
			return ""
		}
		current = next[key]
	}
	return asString(current)
}

func asString(value any) string {
	text, _ := value.(string)
	return text
}
