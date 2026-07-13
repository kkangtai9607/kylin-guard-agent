from __future__ import annotations

import gzip
import hashlib
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path

from backend.app.agent.cleanup import (
    CleanupCandidate,
    CleanupCandidateClassifier,
    CleanupPolicy,
    FileUseState,
)
from backend.app.executor.controlled import ExecutionResult
from backend.app.guardrails.approval import ApprovalTokenManager


class ControlledCleanupExecutor:
    """Production cleanup adapter limited to frozen, pre-classified candidates."""

    def __init__(
        self,
        *,
        policy: CleanupPolicy,
        backup_root: Path,
        approvals: ApprovalTokenManager,
    ) -> None:
        self.classifier = CleanupCandidateClassifier(policy)
        self.backup_root = backup_root.resolve()
        self.backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.approvals = approvals

    def dry_run(
        self, candidate: CleanupCandidate, *, use_state: FileUseState
    ) -> dict[str, object]:
        self._require_current(candidate, use_state)
        return {
            "tool_name": "safe_log_cleanup",
            "candidate_id": candidate.candidate_id,
            "path": candidate.path,
            "size_bytes": candidate.size_bytes,
            "snapshot_hash": candidate.snapshot_hash,
            "risk_level": "L3",
            "requires_approval": True,
            "backup": "gzip archive in protected backup root",
            "verification": "archive digest, target absence and candidate invalidation",
            "rollback": "restore gzip archive to original path",
        }

    def execute(
        self,
        *,
        user_id: str,
        task_id: str,
        candidate: CleanupCandidate,
        approval_token: str,
        use_state: FileUseState,
        simulate_verification_failure: bool = False,
    ) -> ExecutionResult:
        arguments: Mapping[str, object] = {"candidate_id": candidate.candidate_id}
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="safe_log_cleanup",
            arguments=arguments,
        )
        self._require_current(candidate, use_state)
        target = Path(candidate.path)
        change_id = str(uuid.uuid4())
        backup = self.backup_root / f"{change_id}-{target.name}.gz"
        source_digest = self._sha256(target)
        try:
            with target.open("rb") as source, gzip.open(backup, "wb", compresslevel=6) as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if self._gzip_sha256(backup) != source_digest:
                raise ValueError("BACKUP_VERIFICATION_FAILED")
            target.unlink()
            if simulate_verification_failure or target.exists() or not backup.is_file():
                raise ValueError("POSTCONDITION_FAILED")
        except Exception:
            if backup.is_file() and not target.exists():
                self._restore(backup, target)
            raise
        return ExecutionResult(
            change_id=change_id,
            tool_name="safe_log_cleanup",
            status="SUCCEEDED",
            backup_ref=str(backup),
            verification=f"target_absent=true; archived_sha256={source_digest}",
        )

    def rollback(self, *, change_id: str, backup_ref: str, target_path: str) -> ExecutionResult:
        backup = Path(backup_ref).resolve(strict=True)
        if backup.parent != self.backup_root or not backup.name.startswith(f"{change_id}-"):
            raise ValueError("BACKUP_REF_REJECTED")
        target = self.classifier.path_guard.validate(target_path, must_exist=False)
        if target.exists():
            raise ValueError("ROLLBACK_TARGET_EXISTS")
        self._restore(backup, target)
        return ExecutionResult(
            change_id=change_id,
            tool_name="rollback_change",
            status="ROLLED_BACK",
            backup_ref=str(backup),
            verification="target restored from verified gzip archive",
            rollback_status="SUCCEEDED",
        )

    def execute_rollback(
        self,
        *,
        user_id: str,
        task_id: str,
        change_id: str,
        backup_ref: str,
        target_path: str,
        approval_token: str,
    ) -> ExecutionResult:
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="rollback_change",
            arguments={"change_id": change_id},
        )
        return self.rollback(
            change_id=change_id,
            backup_ref=backup_ref,
            target_path=target_path,
        )

    def _require_current(self, candidate: CleanupCandidate, use_state: FileUseState) -> None:
        if not self.classifier.revalidate(candidate, use_state=use_state):
            raise ValueError("CANDIDATE_STALE_OR_UNSAFE")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _gzip_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with gzip.open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _restore(backup: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.restore-{uuid.uuid4().hex}")
        with gzip.open(backup, "rb") as source, temporary.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        temporary.replace(target)
