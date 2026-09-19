import json
import os
import sqlite3

from scripts.backup_sqlite import run_backup


def test_online_backup_has_integrity_manifest_and_retention(tmp_path):
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    data.mkdir()
    with sqlite3.connect(data / "learning.sqlite3") as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('kept')")
    with sqlite3.connect(data / "webhooks.sqlite3") as db:
        db.execute("CREATE TABLE secret_payload (value TEXT)")
        db.execute("INSERT INTO secret_payload VALUES ('do-not-back-up')")

    manifest = run_backup(data, backups, keep=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["files"][0]["source"] == "learning.sqlite3"
    assert len(payload["files"]) == 1
    assert not (manifest.parent / "webhooks.sqlite3").exists()
    assert len(payload["files"][0]["sha256"]) == 64
    with sqlite3.connect(manifest.parent / "learning.sqlite3") as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "kept"
    if os.name != "nt":
        assert (manifest.stat().st_mode & 0o777) == 0o600
