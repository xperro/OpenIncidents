import base64
import gzip
import json
import unittest

from triage.llm_prep import prepare_for_llm


def gcp_envelope(log_entry: dict) -> str:
    encoded = base64.b64encode(json.dumps(log_entry).encode("utf-8")).decode("utf-8")
    return json.dumps({"message": {"data": encoded}})


def aws_envelope(payload: dict) -> str:
    compressed = gzip.compress(json.dumps(payload).encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("utf-8")
    return json.dumps({"awslogs": {"data": encoded}})


class LLMPrepTests(unittest.TestCase):
    def test_prepare_gcp_pubsub_payload(self):
        payload = gcp_envelope(
            {
                "insertId": "1",
                "logName": "projects/demo/logs/run.googleapis.com%2Fstderr",
                "receiveTimestamp": "2026-03-09T03:32:31.640Z",
                "resource": {"labels": {"service_name": "approve-mrs"}},
                "severity": "ERROR",
                "textPayload": "db timeout on postgres",
            }
        )

        prepared = prepare_for_llm(payload, cloud="gcp", runtime_hint="go")

        self.assertEqual(prepared["meta"]["input_events"], 1)
        self.assertEqual(prepared["meta"]["prepared_incidents"], 1)
        incident = prepared["incidents"][0]
        self.assertEqual(incident["cloud"], "gcp")
        self.assertEqual(incident["runtime_hint"], "go")
        self.assertEqual(incident["service"], "approve-mrs")
        self.assertEqual(incident["severity"], "ERROR")
        self.assertIn("timeout", incident["summary"].lower())

    def test_prepare_groups_similar_events(self):
        payload = json.dumps(
            [
                {
                    "severity": "ERROR",
                    "timestamp": "2026-03-09T03:30:00Z",
                    "resource": {"labels": {"service_name": "billing-api"}},
                    "textPayload": "connection refused to redis",
                },
                {
                    "severity": "ERROR",
                    "timestamp": "2026-03-09T03:31:00Z",
                    "resource": {"labels": {"service_name": "billing-api"}},
                    "textPayload": "connection refused to redis",
                },
            ]
        )

        prepared = prepare_for_llm(payload, cloud="gcp", runtime_hint="python")
        self.assertEqual(prepared["meta"]["prepared_incidents"], 1)
        self.assertEqual(prepared["incidents"][0]["count"], 2)

    def test_prepare_aws_cloudwatch_payload(self):
        payload = aws_envelope(
            {
                "owner": "123456789012",
                "logGroup": "/aws/lambda/orders-service",
                "logEvents": [
                    {
                        "id": "evt-1",
                        "timestamp": 1762687901000,
                        "message": "ERROR checkout failed due to timeout",
                    }
                ],
            }
        )
        prepared = prepare_for_llm(payload, cloud="aws", runtime_hint="python")

        self.assertEqual(prepared["meta"]["input_events"], 1)
        self.assertEqual(prepared["meta"]["prepared_incidents"], 1)
        incident = prepared["incidents"][0]
        self.assertEqual(incident["cloud"], "aws")
        self.assertEqual(incident["service"], "orders-service")
        self.assertEqual(incident["severity"], "ERROR")


if __name__ == "__main__":
    unittest.main()
