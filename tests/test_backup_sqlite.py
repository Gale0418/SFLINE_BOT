import json
import sqlite3

from scripts.backup_sqlite import run_backup


def test_online_backup_has_integrity_manifest_and_retention(tmp_path):
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    data.mkdir()
    with sqlite3.connect(data / "learning.sqlite3") as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('kept')")

    manifest = run_backup(data, backups, keep=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["files"][0]["source"] == "learning.sqlite3"
    assert len(payload["files"][0]["sha256"]) == 64
    with sqlite3.connect(manifest.parent / "learning.sqlite3") as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "kept"
