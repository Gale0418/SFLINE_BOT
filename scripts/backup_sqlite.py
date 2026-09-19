"""Create verified online backups for the persistent LINE bot databases."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def backup_database(source: Path, destination: Path) -> dict[str, str | int]:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        check = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"backup integrity check failed: {source.name}")
    payload = destination.read_bytes()
    return {
        "source": source.name,
        "backup": destination.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def run_backup(data_dir: Path, backup_dir: Path, *, keep: int = 14) -> Path:
    if keep < 1:
        raise ValueError("keep must be positive")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = backup_dir / stamp
    records = []
    for name in ("learning.sqlite3", "webhooks.sqlite3"):
        source = data_dir / name
        if source.exists():
            records.append(backup_database(source, run_dir / name))
    if not records:
        raise FileNotFoundError("no persistent SQLite databases found")
    manifest = run_dir / "manifest.json"
    manifest.write_text(
        json.dumps({"created_at": stamp, "files": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    completed = sorted(path for path in backup_dir.iterdir() if (path / "manifest.json").is_file())
    for old in completed[:-keep]:
        for child in old.iterdir():
            child.unlink()
        old.rmdir()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/private"))
    parser.add_argument("--backup-dir", type=Path, default=Path("backups"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    manifest = run_backup(args.data_dir, args.backup_dir, keep=args.keep)
    print(f"backup verified: {manifest}")


if __name__ == "__main__":
    main()
