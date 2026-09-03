from __future__ import annotations

import pytest

from eternal_polaris.config import ConfigurationError, Settings


def test_missing_settings_report_names_only(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "LINE_CHANNEL_SECRET", "LINE_CHANNEL_ACCESS_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_env(tmp_path / "missing.env")
    message = str(caught.value)
    assert "OPENAI_API_KEY" in message
    assert "LINE_CHANNEL_SECRET" in message
    assert "test" not in message


def test_env_loading_does_not_interpolate_secret_values(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "LINE_CHANNEL_SECRET", "LINE_CHANNEL_ACCESS_TOKEN"):
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
