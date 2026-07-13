from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.app.executor.controlled import ExecutionResult
from backend.app.guardrails.approval import ApprovalTokenManager


@dataclass(frozen=True)
class ConfigTarget:
    target_id: str
    path: Path
    validator: str
    validator_path: Path


class ConfigValidator(Protocol):
    def validate(self, target: ConfigTarget, candidate: Path) -> bool: ...


class FixedConfigValidator:
    def validate(self, target: ConfigTarget, candidate: Path) -> bool:
        executable = target.validator_path.resolve(strict=True)
        if target.validator != "nginx" or executable.name != "nginx":
            raise ValueError("VALIDATOR_NOT_ALLOWED")
        completed = subprocess.run(  # noqa: S603
            (str(executable), "-t", "-c", str(candidate)),
            capture_output=True,
            check=False,
            timeout=20,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"},
            cwd="/",
        )
        return completed.returncode == 0


class ControlledConfigExecutor:
    def __init__(
        self,
        *,
        targets: tuple[ConfigTarget, ...],
        backup_root: Path,
        approvals: ApprovalTokenManager,
        validator: ConfigValidator | None = None,
    ) -> None:
        self.targets = {target.target_id: target for target in targets}
        if len(self.targets) != len(targets):
            raise ValueError("DUPLICATE_CONFIG_TARGET")
        self.backup_root = backup_root.resolve()
        self.backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.approvals = approvals
        self.validator = validator or FixedConfigValidator()

    def dry_run(self, target_id: str, content: str) -> dict[str, object]:
        target = self._target(target_id)
        self._validate_content(content)
        current_hash = self._sha256(target.path)
        proposed_hash = hashlib.sha256(content.encode()).hexdigest()
        if target.path.read_text(encoding="utf-8") == content:
            raise ValueError("CONFIG_UNCHANGED")
        return {
            "tool_name": "config_safe_update",
            "target_id": target_id,
            "path": str(target.path),
            "current_hash": current_hash,
            "proposed_hash": proposed_hash,
            "risk_level": "L3",
            "requires_approval": True,
            "backup": "verified copy in protected backup root",
            "verification": f"fixed {target.validator} syntax validator before and after replace",
            "rollback": "atomic restore of verified original copy",
        }

    def execute(
        self,
        *,
        user_id: str,
        task_id: str,
        target_id: str,
        content: str,
        approval_token: str,
    ) -> ExecutionResult:
        target = self._target(target_id)
        self._validate_content(content)
        arguments = {"target_id": target_id, "content": content}
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="config_safe_update",
            arguments=arguments,
        )
        change_id = str(uuid.uuid4())
        backup = self.backup_root / f"{change_id}-{target.path.name}.bak"
        temporary = target.path.with_name(f".{target.path.name}.candidate-{uuid.uuid4().hex}")
        original_hash = self._sha256(target.path)
        try:
            shutil.copy2(target.path, backup)
            if self._sha256(backup) != original_hash:
                raise ValueError("BACKUP_VERIFICATION_FAILED")
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if not self.validator.validate(target, temporary):
                raise ValueError("CONFIG_VALIDATION_FAILED")
            temporary.replace(target.path)
            if not self.validator.validate(target, target.path):
                raise ValueError("POSTCONDITION_FAILED")
        except Exception:
            temporary.unlink(missing_ok=True)
            if backup.is_file() and self._sha256(backup) == original_hash:
                restore = target.path.with_name(f".{target.path.name}.rollback-{uuid.uuid4().hex}")
                shutil.copy2(backup, restore)
                restore.replace(target.path)
            raise
        return ExecutionResult(
            change_id=change_id,
            tool_name="config_safe_update",
            status="SUCCEEDED",
            backup_ref=str(backup),
            verification=f"validator={target.validator}; config_sha256={self._sha256(target.path)}",
        )

    def execute_rollback(
        self,
        *,
        user_id: str,
        task_id: str,
        change_id: str,
        target_id: str,
        backup_ref: str,
        approval_token: str,
    ) -> ExecutionResult:
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="rollback_change",
            arguments={"change_id": change_id},
        )
        target = self._target(target_id)
        backup = Path(backup_ref).resolve(strict=True)
        if backup.parent != self.backup_root or not backup.name.startswith(f"{change_id}-"):
            raise ValueError("BACKUP_REF_REJECTED")
        restore = target.path.with_name(f".{target.path.name}.rollback-{uuid.uuid4().hex}")
        shutil.copy2(backup, restore)
        if not self.validator.validate(target, restore):
            restore.unlink(missing_ok=True)
            raise ValueError("ROLLBACK_VALIDATION_FAILED")
        restore.replace(target.path)
        if not self.validator.validate(target, target.path):
            raise ValueError("ROLLBACK_POSTCONDITION_FAILED")
        return ExecutionResult(
            change_id=change_id,
            tool_name="rollback_change",
            status="ROLLED_BACK",
            backup_ref=str(backup),
            verification=f"target_id={target_id}; restored_sha256={self._sha256(target.path)}",
            rollback_status="SUCCEEDED",
        )

    def _target(self, target_id: str) -> ConfigTarget:
        target = self.targets.get(target_id)
        if target is None:
            raise ValueError("CONFIG_TARGET_NOT_ALLOWED")
        resolved = target.path.resolve(strict=True)
        if resolved != target.path.resolve() or target.path.is_symlink() or not resolved.is_file():
            raise ValueError("CONFIG_TARGET_UNSAFE")
        return ConfigTarget(target.target_id, resolved, target.validator, target.validator_path)

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content.strip() or len(content.encode()) > 1_048_576 or "\x00" in content:
            raise ValueError("CONFIG_CONTENT_INVALID")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
