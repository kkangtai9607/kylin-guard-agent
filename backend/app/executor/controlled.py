from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from backend.app.guardrails.approval import ApprovalTokenManager


@dataclass(frozen=True)
class ExecutionResult:
    change_id: str
    tool_name: str
    status: str
    backup_ref: str | None
    verification: str
    rollback_status: str | None = None


class DemoControlledExecutor:
    """State-changing tools confined to a caller-provided DEMO sandbox root."""

    def __init__(self, root: Path, approvals: ApprovalTokenManager) -> None:
        self.root = root.resolve()
        self.backup_root = self.root / ".backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.approvals = approvals
        self._candidates: dict[str, Path] = {}
        self._changes: dict[str, tuple[Path, Path | None]] = {}
        self._services: dict[str, str] = {"nginx": "running"}
        self._processes: dict[int, str] = {4242: "demo-worker"}

    def register_candidate(self, path: Path) -> str:
        target = path.resolve(strict=True)
        if target == self.backup_root or self.root not in target.parents or target.is_symlink():
            raise ValueError("PATH_REJECTED")
        candidate_id = str(uuid.uuid4())
        self._candidates[candidate_id] = target
        return candidate_id

    def dry_run(self, tool_name: str, arguments: Mapping[str, object]) -> dict[str, object]:
        self._validate_arguments(tool_name, arguments)
        return {
            "tool_name": tool_name,
            "arguments_hash": hashlib.sha256(self._canonical(arguments).encode()).hexdigest(),
            "requires_approval": True,
            "requires_backup": True,
            "verification": "tool-specific postcondition",
            "rollback": "change_id backup restore",
        }

    def execute(
        self,
        *,
        user_id: str,
        task_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
        approval_token: str,
        fault: str | None = None,
    ) -> ExecutionResult:
        self._validate_arguments(tool_name, arguments)
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name=tool_name,
            arguments=arguments,
        )
        handlers: dict[str, Callable[[Mapping[str, object]], ExecutionResult]] = {
            "safe_log_cleanup": self._safe_log_cleanup,
            "service_restart": self._service_restart,
            "config_safe_update": self._config_safe_update,
            "terminate_process": self._terminate_process,
            "rollback_change": self._rollback_change,
        }
        handler = handlers[tool_name]
        result = handler(arguments)
        if fault == "verification":
            return self.rollback(result.change_id, verification_failure=True)
        return result

    def rollback(self, change_id: str, verification_failure: bool = False) -> ExecutionResult:
        if change_id not in self._changes:
            raise ValueError("CHANGE_NOT_FOUND")
        target, backup = self._changes[change_id]
        if backup is not None and backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            shutil.move(str(backup), str(target))
        return ExecutionResult(
            change_id,
            "rollback_change",
            "ROLLED_BACK",
            str(backup) if backup else None,
            "target restored",
            "SUCCEEDED" if verification_failure else None,
        )

    def _safe_log_cleanup(self, arguments: Mapping[str, object]) -> ExecutionResult:
        target = self._candidate(arguments)
        backup = self._backup_path(target)
        size = target.stat().st_size
        shutil.move(str(target), str(backup))
        change_id = self._record(target, backup)
        return ExecutionResult(
            change_id,
            "safe_log_cleanup",
            "SUCCEEDED",
            str(backup),
            f"released_bytes={size}; target_absent={not target.exists()}",
        )

    def _config_safe_update(self, arguments: Mapping[str, object]) -> ExecutionResult:
        target = self._candidate(arguments)
        content = str(arguments["content"])
        backup = self._backup_path(target)
        shutil.copy2(target, backup)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        if not content.strip():
            temporary.unlink(missing_ok=True)
            raise ValueError("CONFIG_VALIDATION_FAILED")
        temporary.replace(target)
        change_id = self._record(target, backup)
        return ExecutionResult(
            change_id,
            "config_safe_update",
            "SUCCEEDED",
            str(backup),
            "non-empty config and atomic replace verified",
        )

    def _service_restart(self, arguments: Mapping[str, object]) -> ExecutionResult:
        service = str(arguments["service"])
        self._services[service] = "running"
        change_id = self._record(self.root / f"service-{service}", None)
        return ExecutionResult(
            change_id, "service_restart", "SUCCEEDED", None, "demo service running"
        )

    def _terminate_process(self, arguments: Mapping[str, object]) -> ExecutionResult:
        pid = self._pid(arguments["pid"])
        self._processes.pop(pid)
        change_id = self._record(self.root / f"process-{pid}", None)
        return ExecutionResult(
            change_id, "terminate_process", "SUCCEEDED", None, "demo process absent"
        )

    def _rollback_change(self, arguments: Mapping[str, object]) -> ExecutionResult:
        return self.rollback(str(arguments["change_id"]))

    def _validate_arguments(self, tool_name: str, arguments: Mapping[str, object]) -> None:
        schemas = {
            "safe_log_cleanup": {"candidate_id"},
            "service_restart": {"service"},
            "config_safe_update": {"candidate_id", "content"},
            "terminate_process": {"pid"},
            "rollback_change": {"change_id"},
        }
        if tool_name not in schemas or set(arguments) != schemas[tool_name]:
            raise ValueError("ARGUMENT_SCHEMA_INVALID")
        if tool_name in {"safe_log_cleanup", "config_safe_update"}:
            self._candidate(arguments)
        if tool_name == "service_restart" and arguments["service"] not in self._services:
            raise ValueError("SERVICE_NOT_ALLOWED")
        if tool_name == "terminate_process":
            pid = self._pid(arguments["pid"])
            if pid in {0, 1} or pid not in self._processes:
                raise ValueError("PROCESS_PROTECTED_OR_MISSING")

    def _candidate(self, arguments: Mapping[str, object]) -> Path:
        candidate_id = str(arguments["candidate_id"])
        if candidate_id not in self._candidates:
            raise ValueError("CANDIDATE_NOT_FOUND")
        return self._candidates[candidate_id]

    def _backup_path(self, target: Path) -> Path:
        return self.backup_root / f"{uuid.uuid4()}-{target.name}"

    def _record(self, target: Path, backup: Path | None) -> str:
        change_id = str(uuid.uuid4())
        self._changes[change_id] = (target, backup)
        return change_id

    @staticmethod
    def _canonical(arguments: Mapping[str, object]) -> str:
        return json.dumps(arguments, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _pid(value: object) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("ARGUMENT_SCHEMA_INVALID")
        return value
