"""Create verified online backups for the persistent LINE bot databases."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def _is_symlink_or_junction(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction is not None and is_junction():
            return True
        info = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        # Failure to inspect a path must never make it eligible for cleanup.
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_point)


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _close_quietly(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _assert_no_link_components(path: Path) -> None:
    """Reject symlink/reparse components before any write follows the path."""
    absolute = _absolute_path(path)
    for component in reversed((absolute, *absolute.parents)):
        if _is_symlink_or_junction(component):
            raise ValueError(f"symlink or junction is not allowed in backup path: {component}")


def _open_directory_chain(path: Path) -> int:
    """Open/create each POSIX directory component without following links."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            try:
                child_fd = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    # Another creator won the race; reopen without following links.
                    pass
                child_fd = os.open(component, flags, dir_fd=descriptor)
            previous_fd = descriptor
            descriptor = child_fd
            os.close(previous_fd)
        return descriptor
    except Exception:
        _close_quietly(descriptor)
        raise


def _prepare_backup_root(path: Path) -> tuple[Path, int | None]:
    """Create a private root and keep a directory fd when supported."""
    root = _absolute_path(path)
    _assert_no_link_components(root)

    if os.name == "nt":
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _assert_no_link_components(root)
        if not root.is_dir():
            raise NotADirectoryError(root)
        return root, None

    if _supports_directory_fds():
        parent_fd = _open_directory_chain(root.parent)
        root_fd: int | None = None
        try:
            try:
                os.mkdir(root.name, mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            root_fd = os.open(
                root.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            info = os.fstat(root_fd)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
                raise PermissionError(f"backup root is not owned by the current user: {root}")
            os.fchmod(root_fd, 0o700)
            info = os.fstat(root_fd)
            if stat.S_IMODE(info.st_mode) != 0o700:
                raise PermissionError(f"backup root permissions are not private: {root}")
            _assert_root_still_attached(root, root_fd)
            return root, root_fd
        except Exception:
            if root_fd is not None:
                _close_quietly(root_fd)
            raise
        finally:
            _close_quietly(parent_fd)
        if root_fd is not None:
            _close_quietly(root_fd)

    # Without directory-fd support, refuse writable non-sticky ancestors
    # before using path-based output operations.
    missing: list[Path] = []
    cursor = root
    while True:
        try:
            cursor.lstat()
            break
        except FileNotFoundError:
            missing.append(cursor)
            cursor = cursor.parent
    for parent in root.parents:
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and not info.st_mode & stat.S_ISVTX:
            raise PermissionError(f"unsafe writable backup ancestor without directory-fd support: {parent}")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    _assert_no_link_components(root)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise PermissionError(f"backup root is not owned by the current user: {root}")
    os.chmod(root, 0o700, follow_symlinks=False)
    if stat.S_IMODE(root.lstat().st_mode) != 0o700:
        raise PermissionError(f"backup root permissions are not private: {root}")
    return root, None


def _create_exclusive_file(path: Path, *, mode: int = 0o600) -> int:
    _assert_no_link_components(path.parent)
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, mode)


def _write_manifest(path: Path, text: str) -> None:
    descriptor = _create_exclusive_file(path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(text)
    if os.name == "nt":
        os.chmod(path, 0o600)
    else:
        os.chmod(path, 0o600, follow_symlinks=False)


def _supports_directory_fds() -> bool:
    if os.name == "nt":
        return False
    required = (os.open, os.mkdir, os.unlink, os.rmdir)
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and all(function in os.supports_dir_fd for function in required)
        and os.scandir in os.supports_fd
    )


def _open_run_directory(root_fd: int, name: str) -> int:
    os.mkdir(name, mode=0o700, dir_fd=root_fd)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        dir_fd=root_fd,
    )
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise PermissionError(f"unsafe backup run directory: {name}")
        os.fchmod(descriptor, 0o700)
        return descriptor
    except Exception:
        _close_quietly(descriptor)
        raise


def _assert_root_still_attached(root: Path, descriptor: int) -> None:
    opened = os.fstat(descriptor)
    try:
        current = root.lstat()
    except OSError as exc:
        raise RuntimeError("backup root path changed during run") from exc
    if (
        _is_symlink_or_junction(root)
        or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
    ):
        raise RuntimeError("backup root path changed during run")


def _create_exclusive_file_at(directory_fd: int, name: str) -> int:
    return os.open(
        name,
        os.O_CREAT | os.O_EXCL | os.O_RDWR,
        0o600,
        dir_fd=directory_fd,
    )


def _write_manifest_at(directory_fd: int, name: str, text: str) -> None:
    descriptor = _create_exclusive_file_at(directory_fd, name)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(text)
    except Exception:
        _close_quietly(descriptor)
        raise


def _completed_names_at(root_fd: int) -> list[str]:
    completed: list[str] = []
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.scandir(root_fd) as entries:
        for entry in entries:
            try:
                child_fd = os.open(entry.name, directory_flags, dir_fd=root_fd)
            except OSError:
                continue
            try:
                try:
                    manifest_fd = os.open("manifest.json", file_flags, dir_fd=child_fd)
                except OSError:
                    continue
                try:
                    if stat.S_ISREG(os.fstat(manifest_fd).st_mode):
                        completed.append(entry.name)
                finally:
                    os.close(manifest_fd)
            finally:
                os.close(child_fd)
    return sorted(completed)


def _prune_at(root_fd: int, names: list[str], keep: int) -> None:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    for name in names[:-keep]:
        try:
            child_fd = os.open(name, directory_flags, dir_fd=root_fd)
        except OSError:
            continue
        try:
            with os.scandir(child_fd) as entries:
                for entry in entries:
                    os.unlink(entry.name, dir_fd=child_fd)
        finally:
            os.close(child_fd)
        os.rmdir(name, dir_fd=root_fd)


def _private_temporary_base() -> Path:
    """Choose a temp parent whose entries cannot be renamed by other UIDs."""
    base = _absolute_path(Path(tempfile.gettempdir()))
    _assert_no_link_components(base)
    info = base.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise NotADirectoryError(base)
    if os.name != "nt":
        safe_owner = info.st_uid == os.geteuid() and not (
            info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        )
        safe_sticky = bool(info.st_mode & stat.S_ISVTX)
        if not (safe_owner or safe_sticky):
            raise PermissionError(f"temporary directory parent is not private: {base}")
    return base


def _is_completed_backup(path: Path, backup_root: Path) -> bool:
    """Accept only real, immediate child directories inside the backup root."""
    if _is_symlink_or_junction(path) or not path.is_dir():
        return False
    try:
        root = backup_root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if resolved.parent != root:
        return False
    return (path / "manifest.json").is_file()


def backup_database(
    source: Path,
    destination: Path,
    *,
    directory_fd: int | None = None,
) -> dict[str, str | int]:
    if not source.is_file():
        raise FileNotFoundError(source)
    temp_parent = _private_temporary_base() if os.name != "nt" else None
    with tempfile.TemporaryDirectory(
        prefix="line-bot-backup-", dir=temp_parent
    ) as temp_name:
        temp_dir = Path(temp_name)
        _assert_no_link_components(temp_dir)
        temp_info = temp_dir.lstat()
        if not stat.S_ISDIR(temp_info.st_mode):
            raise NotADirectoryError(temp_dir)
        if os.name != "nt" and (
            temp_info.st_uid != os.geteuid()
            or stat.S_IMODE(temp_info.st_mode) != 0o700
        ):
            raise PermissionError(f"temporary directory is not private: {temp_dir}")
        snapshot = temp_dir / "snapshot.sqlite3"
        with closing(sqlite3.connect(source)) as src:
            with closing(sqlite3.connect(snapshot)) as dst:
                src.backup(dst)
                check = dst.execute("PRAGMA integrity_check").fetchone()[0]
                if check != "ok":
                    raise RuntimeError(f"backup integrity check failed: {source.name}")

        snapshot_fd: int | None = os.open(
            snapshot, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
        output_fd: int | None = None
        try:
            if directory_fd is None:
                _assert_no_link_components(destination.parent)
                destination.parent.mkdir(parents=True, exist_ok=True)
                _assert_no_link_components(destination.parent)
                output_fd = _create_exclusive_file(destination)
            else:
                output_fd = _create_exclusive_file_at(directory_fd, destination.name)
            if os.name != "nt":
                os.fchmod(output_fd, 0o600)
            with os.fdopen(snapshot_fd, "rb") as snapshot_file:
                snapshot_fd = None
                with os.fdopen(output_fd, "w+b") as backup_file:
                    output_fd = None
                    shutil.copyfileobj(snapshot_file, backup_file)
                    backup_file.flush()
                    os.fsync(backup_file.fileno())
                    backup_file.seek(0)
                    digest = hashlib.sha256()
                    byte_count = 0
                    while chunk := backup_file.read(1024 * 1024):
                        byte_count += len(chunk)
                        digest.update(chunk)
            if os.name == "nt" and directory_fd is None:
                _assert_no_link_components(destination)
                os.chmod(destination, 0o600)
        finally:
            if snapshot_fd is not None:
                _close_quietly(snapshot_fd)
            if output_fd is not None:
                _close_quietly(output_fd)
    return {
        "source": source.name,
        "backup": destination.name,
        "bytes": byte_count,
        "sha256": digest.hexdigest(),
    }


def run_backup(data_dir: Path, backup_dir: Path, *, keep: int = 14) -> Path:
    if keep < 1:
        raise ValueError("keep must be positive")
    backup_root, root_fd = _prepare_backup_root(backup_dir)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = backup_root / stamp

    run_fd: int | None = None
    try:
        if root_fd is None:
            # Exclusive creation prevents timestamp collisions and pre-planted
            # links from redirecting writes on platforms without dir-fd support.
            run_dir.mkdir(mode=0o700)
            _assert_no_link_components(run_dir)
            if os.name != "nt":
                os.chmod(run_dir, 0o700, follow_symlinks=False)
            output_dir = run_dir
        else:
            run_fd = _open_run_directory(root_fd, stamp)
            output_dir = run_dir

        records = []
        for name in ("learning.sqlite3",):
            source = data_dir / name
            if source.exists():
                records.append(
                    backup_database(
                        source,
                        output_dir / name,
                        directory_fd=run_fd,
                    )
                )
        if not records:
            raise FileNotFoundError("no persistent SQLite databases found")

        manifest_name = "manifest.json"
        manifest = run_dir / manifest_name
        manifest_text = json.dumps(
            {"created_at": stamp, "files": records}, ensure_ascii=False, indent=2
        )
        if run_fd is None:
            _write_manifest(manifest, manifest_text)
            completed = sorted(
                path for path in backup_root.iterdir()
                if _is_completed_backup(path, backup_root)
            )
            for old in completed[:-keep]:
                if not _is_completed_backup(old, backup_root):
                    continue
                for child in old.iterdir():
                    child.unlink()
                old.rmdir()
        else:
            _write_manifest_at(run_fd, manifest_name, manifest_text)
            _prune_at(root_fd, _completed_names_at(root_fd), keep)
            _assert_root_still_attached(backup_root, root_fd)
        return manifest
    finally:
        try:
            if run_fd is not None:
                _close_quietly(run_fd)
        finally:
            if root_fd is not None:
                _close_quietly(root_fd)


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
