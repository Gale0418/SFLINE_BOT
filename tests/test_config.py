from __future__ import annotations

import pytest

from eternal_polaris.config import ConfigurationError, Settings


_ENV_SECRET_NAMES = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
)


def _clear(monkeypatch):
    for name in _ENV_SECRET_NAMES + ("AI_PROVIDER", "OPENAI_MODEL", "GEMINI_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_missing_settings_report_names_only(monkeypatch, tmp_path):
    _clear(monkeypatch)
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_env(tmp_path / "missing.env")
    message = str(caught.value)
    assert "LINE_CHANNEL_SECRET" in message
    assert "test" not in message


def test_missing_ai_key_is_rejected_after_line_secrets(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY.*OPENAI_API_KEY"):
        Settings.from_env(env_file)


def test_env_loading_does_not_interpolate_secret_values(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=openai\n"
        "OPENAI_API_KEY=value-${SHOULD_NOT_EXPAND}\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    settings = Settings.from_env(env_file)
    assert settings.ai_provider == "openai"
    assert settings.openai_api_key == "value-${SHOULD_NOT_EXPAND}"
    assert settings.openai_model == "gpt-5.6-luna"
    assert settings.openai_timeout_seconds == 5.0
    assert settings.quiz_ttl_seconds == 1800


def test_auto_prefers_google_free_key(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=auto\n"
        "GEMINI_API_KEY=google-secret\n"
        "OPENAI_API_KEY=openai-secret\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    settings = Settings.from_env(env_file)
    assert settings.ai_provider == "google"
    assert settings.openai_api_key == "google-secret"
    assert settings.openai_model == "gemma-4-31b-it"


def test_google_api_key_alias_is_supported(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=google\n"
        "GOOGLE_API_KEY=google-secret\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    settings = Settings.from_env(env_file)
    assert settings.ai_provider == "google"
    assert settings.gemini_api_key == "google-secret"


def test_explicit_openai_never_silently_switches_to_google(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=openai\n"
        "GEMINI_API_KEY=google-secret\n"
        "OPENAI_API_KEY=openai-secret\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    settings = Settings.from_env(env_file)
    assert settings.ai_provider == "openai"
    assert settings.openai_api_key == "openai-secret"
    assert settings.openai_model == "gpt-5.6-luna"


def test_provider_model_mismatch_is_rejected():
    with pytest.raises(ConfigurationError, match="GEMINI_MODEL"):
        Settings(
            "unused",
            "secret",
            "token",
            ai_provider="google",
            gemini_api_key="google-key",
            gemini_model="gpt-5.6-luna",
        )
    with pytest.raises(ConfigurationError, match="OPENAI_MODEL"):
        Settings(
            "openai-key",
            "secret",
            "token",
            ai_provider="openai",
            openai_model="gemma-4-31b-it",
        )


def test_invalid_provider_is_rejected(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=magic\n"
        "OPENAI_API_KEY=openai-secret\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="AI_PROVIDER"):
        Settings.from_env(env_file)


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
