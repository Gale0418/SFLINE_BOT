from __future__ import annotations

import pytest

from eternal_polaris.config import ConfigurationError, Settings


_SECRET_NAMES = ("OPENAI_API_KEY", "LINE_CHANNEL_SECRET", "LINE_CHANNEL_ACCESS_TOKEN")


def test_missing_settings_report_names_only(monkeypatch, tmp_path):
    for name in _SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_env(tmp_path / "missing.env")
    message = str(caught.value)
    assert "OPENAI_API_KEY" in message
    assert "LINE_CHANNEL_SECRET" in message
    assert "test" not in message


def test_env_loading_does_not_interpolate_secret_values(monkeypatch, tmp_path):
    for name in _SECRET_NAMES:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=value-${SHOULD_NOT_EXPAND}\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    settings = Settings.from_env(env_file)
    assert settings.openai_api_key == "value-${SHOULD_NOT_EXPAND}"
    assert settings.openai_timeout_seconds == 5.0
    assert settings.quiz_ttl_seconds == 1800


def test_default_latency_budget_is_safe():
    settings = Settings("openai", "secret", "token")
    assert settings.webhook_worker_threads == 4
    assert settings.webhook_queue_capacity == 4


def test_unsafe_reply_token_latency_budget_is_rejected():
    with pytest.raises(ConfigurationError, match="reply token"):
        Settings(
            "openai",
            "secret",
            "token",
            openai_timeout_seconds=15,
            line_reply_timeout_seconds=2,
            webhook_worker_threads=1,
            webhook_queue_capacity=3,
            webhook_max_pending_per_key=3,
        )


def test_numeric_ranges_are_validated():
    with pytest.raises(ConfigurationError):
        Settings("openai", "secret", "token", quiz_ttl_seconds=0)
    with pytest.raises(ConfigurationError):
        Settings("openai", "secret", "token", line_reply_timeout_seconds=0)
