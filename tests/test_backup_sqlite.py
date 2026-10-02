import json
import os
import sqlite3
import stat
from datetime import UTC, datetime

import pytest

from scripts import backup_sqlite
from scripts.backup_sqlite import backup_database, run_backup


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
        assert stat.S_IMODE(backups.stat().st_mode) == 0o700
        assert backups.stat().st_uid == os.geteuid()


def test_retention_ignores_directory_symlinks_outside_backup_root(tmp_path):
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    outside = tmp_path / "outside"
    data.mkdir()
    backups.mkdir()
    outside.mkdir()
    with sqlite3.connect(data / "learning.sqlite3") as db:
        db.execute("CREATE TABLE sample (value TEXT)")

    old_backup = backups / "20000101T000000Z"
    old_backup.mkdir()
    (old_backup / "manifest.json").write_text("{}", encoding="utf-8")
    (outside / "manifest.json").write_text("{}", encoding="utf-8")
    sentinel = outside / "keep.txt"
    sentinel.write_text("outside backup root", encoding="utf-8")
    outside_link = backups / "20010101T000000Z"
    try:
        outside_link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"cannot create directory symlink on this host: {exc}")

    run_backup(data, backups, keep=1)

    assert sentinel.read_text(encoding="utf-8") == "outside backup root"
    assert (outside / "manifest.json").exists()
    assert outside_link.is_symlink()
    assert not old_backup.exists()


def _source_database(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('source')")


class _FixedDateTime:
    @staticmethod
    def now(tz):
        return datetime(2026, 10, 2, 12, 0, 0, tzinfo=tz)


@pytest.mark.parametrize("link_location", ["root", "ancestor"])
def test_backup_rejects_symlink_in_root_path_without_creating_outside(tmp_path, link_location):
    if os.name == "nt":
        pytest.skip("POSIX symlink permission behavior is not available")
    data = tmp_path / "data"
    outside = tmp_path / "outside"
    data.mkdir()
    outside.mkdir()
    _source_database(data / "learning.sqlite3")

    if link_location == "root":
        link = tmp_path / "backup-link"
        link.symlink_to(outside, target_is_directory=True)
        backup_path = link
    else:
        link = tmp_path / "parent-link"
        link.symlink_to(outside, target_is_directory=True)
        backup_path = link / "backups"

    with pytest.raises(ValueError, match="symlink or junction"):
        run_backup(data, backup_path)

    assert list(outside.iterdir()) == []


def test_backup_refuses_timestamp_link_without_writing_outside(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip("POSIX symlink permission behavior is not available")
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    outside = tmp_path / "outside"
    data.mkdir()
    backups.mkdir()
    outside.mkdir()
    _source_database(data / "learning.sqlite3")
    sentinel = outside / "keep.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    stamp = "20261002T120000Z"
    (backups / stamp).symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(backup_sqlite, "datetime", _FixedDateTime)

    with pytest.raises(FileExistsError):
        run_backup(data, backups)

    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (outside / "learning.sqlite3").exists()
    assert not (outside / "manifest.json").exists()


def test_backup_database_refuses_existing_destination_symlink(tmp_path):
    if os.name == "nt":
        pytest.skip("POSIX symlink permission behavior is not available")
    source = tmp_path / "source.sqlite3"
    outside = tmp_path / "outside.sqlite3"
    destination = tmp_path / "backups" / "learning.sqlite3"
    _source_database(source)
    _source_database(outside)
    destination.parent.mkdir()
    destination.symlink_to(outside)

    with pytest.raises(FileExistsError):
        backup_database(source, destination)

    with sqlite3.connect(outside) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "source"


def test_same_timestamp_collision_preserves_existing_backup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    data.mkdir()
    _source_database(data / "learning.sqlite3")
    monkeypatch.setattr(backup_sqlite, "datetime", _FixedDateTime)
    first_manifest = run_backup(data, backups)
    original_manifest = first_manifest.read_bytes()
    original_backup = (first_manifest.parent / "learning.sqlite3").read_bytes()

    with pytest.raises(FileExistsError):
        run_backup(data, backups)

    assert first_manifest.read_bytes() == original_manifest
    assert (first_manifest.parent / "learning.sqlite3").read_bytes() == original_backup


def test_snapshot_copy_stays_anchored_if_root_path_is_replaced(tmp_path, monkeypatch):
    if (
        os.name == "nt"
        or not backup_sqlite._supports_directory_fds()
    ):
        pytest.skip("requires POSIX directory descriptors")
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    moved_root = tmp_path / "moved-backups"
    outside = tmp_path / "outside"
    data.mkdir()
    outside.mkdir()
    (outside / "20261002T120000Z").mkdir()
    _source_database(data / "learning.sqlite3")
    sentinel = outside / "keep.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    monkeypatch.setattr(backup_sqlite, "datetime", _FixedDateTime)
    real_backup_database = backup_sqlite.backup_database

    def rename_root_before_database(source, destination, *, directory_fd=None):
        backups.rename(moved_root)
        backups.symlink_to(outside, target_is_directory=True)
        return real_backup_database(source, destination, directory_fd=directory_fd)

    monkeypatch.setattr(backup_sqlite, "backup_database", rename_root_before_database)

    with pytest.raises(RuntimeError, match="backup root path changed"):
        run_backup(data, backups)

    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (outside / "20261002T120000Z" / "learning.sqlite3").exists()
    assert not (outside / "20261002T120000Z" / "manifest.json").exists()
    saved_run = moved_root / "20261002T120000Z"
    assert (saved_run / "learning.sqlite3").is_file()
    assert (saved_run / "manifest.json").is_file()


def test_manifest_creation_refuses_existing_symlink(tmp_path):
    if os.name == "nt":
        pytest.skip("POSIX symlink permission behavior is not available")
    target = tmp_path / "outside.txt"
    target.write_text("preserve", encoding="utf-8")
    link = tmp_path / "manifest.json"
    link.symlink_to(target)

    with pytest.raises(FileExistsError):
        backup_sqlite._write_manifest(link, "replacement")

    assert target.read_text(encoding="utf-8") == "preserve"


def test_private_root_works_under_shared_mode_parent_without_chmod(tmp_path):
    if (
        os.name == "nt"
        or not backup_sqlite._supports_directory_fds()
    ):
        pytest.skip("requires POSIX directory descriptors")
    data = tmp_path / "data"
    shared_parent = tmp_path / "shared"
    backups = shared_parent / "backups"
    data.mkdir()
    shared_parent.mkdir()
    os.chmod(shared_parent, 0o777)
    _source_database(data / "learning.sqlite3")

    run_backup(data, backups)

    assert stat.S_IMODE(shared_parent.stat().st_mode) == 0o777
    assert stat.S_IMODE(backups.stat().st_mode) == 0o700
