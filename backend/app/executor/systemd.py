from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from backend.app.executor.controlled import ExecutionResult
from backend.app.guardrails.approval import ApprovalTokenManager


@dataclass(frozen=True)
class CommandOutcome:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def run(self, argv: tuple[str, ...], *, timeout: int) -> CommandOutcome: ...


@runtime_checkable
class BrokeredServiceRunner(Protocol):
    def restart_with_approval(
        self, *, service: str, user_id: str, task_id: str, approval_token: str
    ) -> CommandOutcome: ...

    def rollback_with_approval(
        self,
        *,
        service: str,
        user_id: str,
        task_id: str,
        change_id: str,
        approval_token: str,
    ) -> CommandOutcome: ...


class FixedSystemctlRunner:
    def __init__(self, executable: Path) -> None:
        self.executable = executable.resolve(strict=True)
        if not self.executable.is_absolute() or self.executable.name != "systemctl":
            raise ValueError("SYSTEMCTL_PATH_REJECTED")

    def run(self, argv: tuple[str, ...], *, timeout: int) -> CommandOutcome:
        if not argv or Path(argv[0]).resolve() != self.executable:
            raise ValueError("EXECUTABLE_NOT_ALLOWED")
        if len(argv) != 3 or argv[1] not in {"is-active", "restart", "start", "stop"}:
            raise ValueError("SYSTEMCTL_ARGUMENTS_REJECTED")
        completed = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            check=False,
            timeout=timeout,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
            cwd="/",
        )
        return CommandOutcome(
            returncode=completed.returncode,
            stdout=completed.stdout[:65536].decode(errors="replace"),
            stderr=completed.stderr[:65536].decode(errors="replace"),
        )


class ControlledServiceExecutor:
    def __init__(
        self,
        *,
        executable: Path,
        allowed_services: tuple[str, ...],
        approvals: ApprovalTokenManager,
        runner: CommandRunner | None = None,
    ) -> None:
        self.executable = executable
        self.allowed_services = frozenset(allowed_services)
        self.approvals = approvals
        self.runner = runner or FixedSystemctlRunner(executable)

    def dry_run(self, service: str) -> dict[str, object]:
        self._validate_service(service)
        before = self._is_active(service)
        if not before:
            raise ValueError("SERVICE_NOT_ACTIVE")
        return {
            "tool_name": "service_restart",
            "service": service,
            "risk_level": "L3",
            "requires_approval": True,
            "state_snapshot": {"active": True},
            "argv_template": [str(self.executable), "restart", "<allowlisted-service>"],
            "verification": "systemctl is-active",
            "rollback": "restore captured active state",
        }

    def execute(
        self,
        *,
        user_id: str,
        task_id: str,
        service: str,
        approval_token: str,
    ) -> ExecutionResult:
        self._validate_service(service)
        if not self._is_active(service):
            raise ValueError("SERVICE_STATE_CHANGED")
        if isinstance(self.runner, BrokeredServiceRunner):
            outcome = self.runner.restart_with_approval(
                service=service,
                user_id=user_id,
                task_id=task_id,
                approval_token=approval_token,
            )
        else:
            self.approvals.consume(
                approval_token,
                user_id=user_id,
                task_id=task_id,
                tool_name="service_restart",
                arguments={"service": service},
            )
            outcome = self.runner.run((str(self.executable), "restart", service), timeout=30)
        if outcome.returncode != 0 or not self._is_active(service):
            if isinstance(self.runner, BrokeredServiceRunner):
                raise ValueError("SERVICE_RESTART_FAILED_ROLLED_BACK")
            rollback = self.runner.run((str(self.executable), "start", service), timeout=30)
            if rollback.returncode != 0 or not self._is_active(service):
                raise ValueError("SERVICE_RESTART_AND_ROLLBACK_FAILED")
            raise ValueError("SERVICE_RESTART_FAILED_ROLLED_BACK")
        return ExecutionResult(
            change_id=str(uuid.uuid4()),
            tool_name="service_restart",
            status="SUCCEEDED",
            backup_ref=None,
            verification=f"service={service}; active=true; state_snapshot=active",
        )

    def restore(self, service: str) -> bool:
        """Internal rollback primitive; callers must enforce their own approval scope."""
        self._validate_service(service)
        outcome = self.runner.run((str(self.executable), "restart", service), timeout=30)
        return outcome.returncode == 0 and self._is_active(service)

    def execute_rollback(
        self,
        *,
        user_id: str,
        task_id: str,
        change_id: str,
        service: str,
        approval_token: str,
    ) -> ExecutionResult:
        if isinstance(self.runner, BrokeredServiceRunner):
            outcome = self.runner.rollback_with_approval(
                service=service,
                user_id=user_id,
                task_id=task_id,
                change_id=change_id,
                approval_token=approval_token,
            )
            restored = outcome.returncode == 0 and self._is_active(service)
        else:
            self.approvals.consume(
                approval_token,
                user_id=user_id,
                task_id=task_id,
                tool_name="rollback_change",
                arguments={"change_id": change_id},
            )
            restored = self.restore(service)
        if not restored:
            raise ValueError("SERVICE_ROLLBACK_FAILED")
        return ExecutionResult(
            change_id=change_id,
            tool_name="rollback_change",
            status="ROLLED_BACK",
            backup_ref=None,
            verification=f"service={service}; active=true; rollback_restart_verified=true",
            rollback_status="SUCCEEDED",
        )

    def _is_active(self, service: str) -> bool:
        outcome = self.runner.run((str(self.executable), "is-active", service), timeout=10)
        return outcome.returncode == 0 and outcome.stdout.strip() == "active"

    def _validate_service(self, service: str) -> None:
        if service not in self.allowed_services:
            raise ValueError("SERVICE_NOT_ALLOWED")
        if not service or len(service) > 128 or any(char.isspace() for char in service):
            raise ValueError("SERVICE_NAME_INVALID")
