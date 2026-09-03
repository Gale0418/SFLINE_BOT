from __future__ import annotations

import pytest

from eternal_polaris.secret_migration import SecretMigrationError, migrate


def test_migration_is_atomic_and_does_not_print_values(tmp_path):
    ngrok = tmp_path / "ngrok.txt"
    app = tmp_path / "app.txt"
    output = tmp_path / ".env"
    ngrok.write_text("ngrok-secret\n", encoding="utf-8")
    app.write_text(
        "OPENAI_API_KEY=openai-secret\n"
        "LINE_CHANNEL_SECRET=line-secret\n"
        "LINE_CHANNEL_ACCESS_TOKEN=line-token\n",
        encoding="utf-8",
    )
    names = migrate(ngrok, app, output)
    assert len(names) == 4
    text = output.read_text(encoding="utf-8")
    assert "NGROK_AUTHTOKEN=" in text
    assert ngrok.exists() and app.exists()


def test_migration_refuses_overwrite(tmp_path):
    output = tmp_path / ".env"
    output.write_text("keep=true", encoding="utf-8")
    with pytest.raises(SecretMigrationError, match="拒絕覆寫"):
        migrate(tmp_path / "missing-a", tmp_path / "missing-b", output)
    assert output.read_text(encoding="utf-8") == "keep=true"


def test_migration_rejects_unnamed_app_secret(tmp_path):
    ngrok = tmp_path / "ngrok.txt"
    app = tmp_path / "app.txt"
    ngrok.write_text("token\n", encoding="utf-8")
    app.write_text("mystery\n", encoding="utf-8")
    with pytest.raises(SecretMigrationError, match="無法判定"):
        migrate(ngrok, app, tmp_path / ".env")

