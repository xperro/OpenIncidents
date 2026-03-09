import unittest
from unittest import mock

from triage.notifier import build_discord_payload, iter_results, send_http_json


class NotifierTests(unittest.TestCase):
    def test_send_http_json_sets_user_agent_and_accept(self):
        captured = {}

        class FakeResponse:
            status = 204

            def read(self):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout=20):
            captured["user_agent"] = request.headers.get("User-agent")
            captured["accept"] = request.headers.get("Accept")
            captured["content_type"] = request.headers.get("Content-type")
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = send_http_json(
                "discord",
                "https://discord.com/api/webhooks/test",
                {"content": "hello"},
                headers={},
                dry_run=False,
            )

        self.assertEqual(result["status"], "sent")
        self.assertIn("OpenIncidents-Triage/1.0", captured["user_agent"])
        self.assertIn("application/json", captured["accept"])
        self.assertEqual(captured["content_type"], "application/json")

    def test_build_discord_payload_uses_embed_card(self):
        result = {
            "incident_id": "abc123",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "service": "approve-mrs",
            "severity": "ERROR",
            "analysis": {
                "summary": "DB timeout",
                "suspected_cause": "Connection pool saturation",
                "suggested_fix": "Increase pool and optimize query",
                "confidence": 0.8,
                "files_or_area_to_check": ["internal/db/repository.go"],
                "tests_to_run": ["integration test"],
            },
        }
        payload = build_discord_payload(result, language="spanish")
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]
        self.assertIn("[ERROR]", embed["title"])
        self.assertEqual(embed["fields"][1]["name"], "**Gravedad**")
        self.assertEqual(embed["fields"][1]["value"], "ERROR")

    def test_iter_results_orders_by_severity_desc(self):
        payload = {
            "results": [
                {"incident_id": "i1", "severity": "WARNING", "analysis": {"summary": "warn"}},
                {"incident_id": "i2", "severity": "CRITICAL", "analysis": {"summary": "crit"}},
                {"incident_id": "i3", "severity": "ERROR", "analysis": {"summary": "err"}},
            ]
        }
        ordered = iter_results(payload)
        self.assertEqual([item["incident_id"] for item in ordered], ["i2", "i3", "i1"])


if __name__ == "__main__":
    unittest.main()
