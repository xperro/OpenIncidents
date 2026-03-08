"""Per-user local state handling for the ``triage`` CLI."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from typing import Any

from .constants import SCHEMA_VERSION, VALID_CLOUDS, VALID_LLM_PROVIDERS
from .errors import UserError

SECRET_SENTINEL = "***REDACTED***"


def local_home() -> str:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, "triage")
        return os.path.join(os.path.expanduser("~"), "triage")
    return os.path.join(os.path.expanduser("~"), ".triage")


def state_path() -> str:
    return os.path.join(local_home(), "config.json")


def new_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "bootstrap_complete": False,
        "default_cloud": None,
        "clouds": {
            "gcp": {"enabled": False},
            "aws": {"enabled": False},
        },
        "llm": {
            "provider": None,
            "model": None,
            "api_key_env": None,
            "api_key_value": None,
        },
    }


def normalize_state(data: dict[str, Any] | None) -> dict[str, Any]:
    state = new_state()
    if not data:
        return state
    state["schema_version"] = data.get("schema_version", SCHEMA_VERSION)
    state["default_cloud"] = data.get("default_cloud")
    clouds = data.get("clouds", {})
    for cloud in VALID_CLOUDS:
        state["clouds"][cloud]["enabled"] = bool(
            clouds.get(cloud, {}).get("enabled", False)
        )
    llm = data.get("llm", {})
    state["llm"]["provider"] = llm.get("provider")
    state["llm"]["model"] = llm.get("model")
    state["llm"]["api_key_env"] = llm.get("api_key_env")
    state["llm"]["api_key_value"] = llm.get("api_key_value")
    recompute_bootstrap_complete(state)
    return state


def load_state(optional: bool = False) -> dict[str, Any] | None:
    path = state_path()
    if not os.path.exists(path):
        if optional:
            return None
        raise UserError(
            "Local CLI state does not exist yet. Run `triage init` first."
        )
    with open(path, "r", encoding="utf-8") as handle:
        return normalize_state(json.load(handle))


def ensure_local_home() -> None:
    path = local_home()
    os.makedirs(path, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass


def save_state(state: dict[str, Any]) -> None:
    ensure_local_home()
    recompute_bootstrap_complete(state)
    payload = json.dumps(state, indent=2, sort_keys=True)
    directory = local_home()
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix="config.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
        if os.name != "nt":
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
        os.replace(temp_path, state_path())
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def llm_env_name(provider: str | None) -> str | None:
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    return None


def recompute_bootstrap_complete(state: dict[str, Any]) -> None:
    clouds_ok = any(bool(state["clouds"][cloud]["enabled"]) for cloud in VALID_CLOUDS)
    llm = state["llm"]
    provider = llm.get("provider")
    provider_ok = provider in VALID_LLM_PROVIDERS
    if provider in ("openai", "anthropic"):
        provider_ok = provider_ok and bool(llm.get("model")) and bool(
            llm.get("api_key_value")
        )
    state["bootstrap_complete"] = bool(clouds_ok and provider_ok)


def redacted_state(state: dict[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_state(state)
    payload = copy.deepcopy(normalized)
    if payload["llm"].get("api_key_value"):
        payload["llm"]["api_key_value"] = SECRET_SENTINEL
    return payload


def apply_setting(state: dict[str, Any], key: str, value: str) -> None:
    if key == "default_cloud":
        if value not in VALID_CLOUDS:
            raise UserError("`default_cloud` must be `gcp` or `aws`.")
        state["default_cloud"] = value
    elif key == "llm.provider":
        if value not in VALID_LLM_PROVIDERS:
            raise UserError("`llm.provider` must be `none`, `openai`, or `anthropic`.")
        state["llm"]["provider"] = value
        state["llm"]["api_key_env"] = llm_env_name(value)
        if value == "none":
            state["llm"]["model"] = None
            state["llm"]["api_key_value"] = None
    elif key == "llm.model":
        state["llm"]["model"] = value
    elif key == "llm.api_key":
        state["llm"]["api_key_value"] = value
    else:
        raise UserError(
            "Unsupported key. Writable keys: default_cloud, llm.provider, "
            "llm.model, llm.api_key."
        )
    recompute_bootstrap_complete(state)


def state_exists() -> bool:
    return os.path.exists(state_path())
