import json
import unittest
from unittest import mock

from triage.llm_request import build_llm_request_payload, run_llm_client


class LLMRequestTests(unittest.TestCase):
    def test_build_llm_request_payload(self):
        prepared = {
            "schema_version": "llm-prep.v1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "cloud": "gcp",
                    "runtime_hint": "go",
                    "severity": "ERROR",
                    "count": 2,
                    "window": {"first_seen": "2026-03-09T15:00:00Z", "last_seen": "2026-03-09T15:02:00Z"},
                    "summary": "db timeout on postgres",
                    "error_message": "db timeout on postgres",
                    "stacktrace_excerpt": "",
                    "source_link": "",
                    "llm_input": {"incident_summary": "db timeout on postgres", "evidence": ["event-1"]},
                }
            ],
        }

        payload = build_llm_request_payload(prepared, provider="mock", model="mock-1", max_tokens=900)
        self.assertEqual(payload["schema_version"], "llm-request.v1")
        self.assertEqual(payload["provider"], "mock")
        self.assertEqual(payload["model"], "mock-1")
        self.assertEqual(len(payload["incidents"]), 1)
        self.assertEqual(payload["incidents"][0]["constraints"]["max_tokens"], 900)

    def test_run_llm_client_mock(self):
        request_payload = {
            "schema_version": "llm-request.v1",
            "request_id": "llmreq-1",
            "provider": "mock",
            "model": "mock-1",
            "incidents": [
                {
                    "incident_id": "abc123",
                    "service": "approve-mrs",
                    "severity": "ERROR",
                    "incident_summary": "db timeout on postgres",
                    "evidence": ["event-1"],
                }
            ],
        }

        analysis = run_llm_client(request_payload, provider="mock")
        self.assertEqual(analysis["schema_version"], "llm-analysis.v1")
        self.assertEqual(analysis["provider"], "mock")
        self.assertEqual(len(analysis["results"]), 1)
        self.assertIn("suggested_fix", analysis["results"][0]["analysis"])
        # Ensure output remains JSON-serializable.
        json.dumps(analysis)

    def test_run_llm_client_uses_injected_env_for_api_key(self):
        request_payload = {
            "schema_version": "llm-request.v1",
            "request_id": "llmreq-2",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "incidents": [
                {
                    "incident_id": "abc124",
                    "service": "approve-mrs",
                    "severity": "ERROR",
                    "incident_summary": "db timeout on postgres",
                    "evidence": ["event-1"],
                }
            ],
        }

        with mock.patch("triage.llm_request.client.call_openai", return_value='{"summary":"ok"}'):
            analysis = run_llm_client(
                request_payload,
                provider="openai",
                env={"OPENAI_API_KEY": "sk-test"},
            )
        self.assertEqual(analysis["provider"], "openai")
        self.assertEqual(len(analysis["results"]), 1)


if __name__ == "__main__":
    unittest.main()
