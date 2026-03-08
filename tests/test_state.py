import os
import tempfile
import unittest
from unittest import mock

from triage.state import (
    SECRET_SENTINEL,
    apply_setting,
    load_state,
    new_state,
    redacted_state,
    save_state,
)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        patcher = mock.patch.dict(
            os.environ,
            {
                "HOME": self.temp_dir.name,
                "APPDATA": self.temp_dir.name,
                "USERPROFILE": self.temp_dir.name,
            },
            clear=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_and_load_state(self):
        state = new_state()
        state["default_cloud"] = "gcp"
        state["clouds"]["gcp"]["enabled"] = True
        state["llm"]["provider"] = "none"

        save_state(state)
        loaded = load_state()

        self.assertTrue(loaded["bootstrap_complete"])
        self.assertEqual(loaded["default_cloud"], "gcp")

    def test_redacted_state_hides_api_key(self):
        state = new_state()
        state["llm"]["provider"] = "openai"
        state["llm"]["model"] = "gpt-4.1"
        state["llm"]["api_key_env"] = "OPENAI_API_KEY"
        state["llm"]["api_key_value"] = "secret-value"
        redacted = redacted_state(state)

        self.assertEqual(redacted["llm"]["api_key_value"], SECRET_SENTINEL)

    def test_apply_setting_recomputes_bootstrap(self):
        state = new_state()
        state["clouds"]["gcp"]["enabled"] = True
        apply_setting(state, "llm.provider", "openai")
        apply_setting(state, "llm.model", "gpt-4.1")
        apply_setting(state, "llm.api_key", "secret")

        self.assertTrue(state["bootstrap_complete"])


if __name__ == "__main__":
    unittest.main()
