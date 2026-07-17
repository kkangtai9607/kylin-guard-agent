#!/usr/bin/env python3
"""Root-owned, fixed-argument helper. It intentionally exposes no generic command API."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

_RESTART = ("service_restart", "nginx")
_ROLLBACK = ("service_rollback", "nginx")
_CLEANUP = "safe_log_cleanup"
_CLEANUP_ROLLBACK = "cleanup_rollback"
_SYSTEMCTL = "/usr/bin/systemctl"
_ALLOWED_SUFFIXES = (
    ".log",
    ".gz",
    ".old",
    ".tmp",
    ".cache",
    ".msi",
    ".iso",
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
    ".7z",
    ".rar",
    ".rpm",
    ".deb",
    ".apk",
    ".dmg",
    ".pkg",
    ".exe",
)
_FORBIDDEN_TERMS = (
    "audit",
    "journal",
    "mysql-bin",
    "binlog",
    "postgresql",
    "transaction",
    "redo",
    "wal",
    "secret",
    "token",
    "password",
    "credential",
    "private-key",
    "id_rsa",
)
_PROTECTED_PREFIXES = (
    Path("/etc"),
    Path("/root"),
    Path("/boot"),
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/run"),
    Path("/var/lib"),
)
_FIXED_ALLOWED_ROOTS = (
    Path("/tmp"),  # noqa: S108 - intentional controlled cleanup root.
    Path("/var/tmp"),  # noqa: S108 - intentional controlled cleanup root.
    Path("/var/log"),
    Path("/var/log/kylin-guard-managed"),
)
_HOME_LOW_RISK_DIRS = {".cache", "Downloads", "tmp"}


def main(argv: list[str]) -> int:
    if argv and argv[0] == _CLEANUP:
        return _safe_log_cleanup(argv)
    if argv and argv[0] == _CLEANUP_ROLLBACK:
        return _cleanup_rollback(argv)
    if tuple(argv) not in {_RESTART, _ROLLBACK}:
        return 64
    completed = subprocess.run(  # noqa: S603
        (_SYSTEMCTL, "restart", "nginx"),
        check=False,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        cwd="/",
    )
    if completed.returncode == 0:
        return 0
    recovery = subprocess.run(  # noqa: S603
        (_SYSTEMCTL, "start", "nginx"),
        check=False,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        cwd="/",
    )
    return completed.returncode if recovery.returncode == 0 else 70


def _safe_log_cleanup(argv: list[str]) -> int:
    if len(argv) != 8:
        return 64
    _, candidate_id, raw_path, raw_size, raw_inode, raw_device, snapshot_hash, raw_backup_root = argv
    try:
        if not candidate_id.startswith("cleanup-"):
            raise ValueError("CANDIDATE_ID_REJECTED")
        target = _validate_cleanup_target(raw_path)
        metadata = target.stat(follow_symlinks=False)
        if metadata.st_size != int(raw_size) or metadata.st_ino != int(raw_inode) or metadata.st_dev != int(raw_device):
            raise ValueError("CANDIDATE_STALE_OR_UNSAFE")
        if _snapshot_hash(target, metadata) != snapshot_hash:
            raise ValueError("SNAPSHOT_HASH_MISMATCH")
        backup_root = _validate_backup_root(raw_backup_root)
        change_id = str(uuid.uuid4())
        backup = backup_root / f"{change_id}-{target.name}.gz"
        source_digest = _sha256(target)
        with target.open("rb") as source, gzip.open(backup, "wb", compresslevel=6) as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        os.chmod(backup, 0o600)
        if _gzip_sha256(backup) != source_digest:
            raise ValueError("BACKUP_VERIFICATION_FAILED")
        target.unlink()
        if target.exists():
            raise ValueError("POSTCONDITION_FAILED")
        print(
            json.dumps(
                {
                    "change_id": change_id,
                    "backup_ref": str(backup),
                    "released_bytes": metadata.st_size,
                    "verification": f"target_absent=true; archived_sha256={source_digest}",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as error:
        print(f"CLEANUP_DENIED:{type(error).__name__}", file=sys.stderr)
        return 73


def _cleanup_rollback(argv: list[str]) -> int:
    if len(argv) != 5:
        return 64
    _, change_id, raw_backup, raw_target, raw_backup_root = argv
    try:
        backup_root = _validate_backup_root(raw_backup_root)
        backup = Path(raw_backup).resolve(strict=True)
        if backup.parent != backup_root or not backup.name.startswith(f"{change_id}-"):
            raise ValueError("BACKUP_REF_REJECTED")
        target = _validate_cleanup_target(raw_target, must_exist=False)
        if target.exists():
            raise ValueError("ROLLBACK_TARGET_EXISTS")
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(backup, "rb") as source, target.open("wb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        if not target.is_file():
            raise ValueError("ROLLBACK_POSTCONDITION_FAILED")
        print(
            json.dumps(
                {
                    "change_id": change_id,
                    "backup_ref": str(backup),
                    "verification": "target restored from verified gzip archive",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as error:
        print(f"ROLLBACK_DENIED:{type(error).__name__}", file=sys.stderr)
        return 74


def _validate_cleanup_target(raw_path: str, *, must_exist: bool = True) -> Path:
    source = Path(raw_path)
    if not source.is_absolute():
        raise ValueError("PATH_REJECTED")
    current = source
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("SYMLINK_REJECTED")
        if current.parent == current:
            break
        current = current.parent
    target = source.resolve(strict=must_exist)
    if must_exist and not target.is_file():
        raise ValueError("NOT_REGULAR_FILE")
    if any(target == protected or protected in target.parents for protected in _PROTECTED_PREFIXES):
        raise ValueError("PROTECTED_PATH")
    if not _is_allowed_cleanup_path(target):
        raise ValueError("PATH_REJECTED")
    lowered = target.name.lower()
    if must_exist and not any(lowered.endswith(suffix) for suffix in _ALLOWED_SUFFIXES):
        raise ValueError("FILE_TYPE_NOT_ALLOWED")
    if any(term in lowered for term in _FORBIDDEN_TERMS):
        raise ValueError("CRITICAL_OR_DATABASE_LOG")
    return target


def _is_allowed_cleanup_path(target: Path) -> bool:
    if any(target == root or root in target.parents for root in _FIXED_ALLOWED_ROOTS):
        return True
    parts = target.parts
    if len(parts) >= 4 and parts[1] == "home":
        return any(part in _HOME_LOW_RISK_DIRS for part in parts[3:-1])
    return False


def _validate_backup_root(raw_path: str) -> Path:
    root = Path(raw_path).resolve()
    expected = Path("/var/lib/kylin-guard/backups")
    if root != expected:
        raise ValueError("BACKUP_ROOT_REJECTED")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _snapshot_hash(path: Path, metadata: os.stat_result) -> str:
    snapshot = {
        "path": str(path),
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "inode": metadata.st_ino,
        "device": metadata.st_dev,
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gzip_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
