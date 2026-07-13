from __future__ import annotations

import hashlib
import json
import os
import signal
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.app.executor.controlled import ExecutionResult
from backend.app.guardrails.approval import ApprovalTokenManager


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    name: str
    start_ticks: int


@dataclass(frozen=True)
class ProcessCandidate:
    candidate_id: str
    pid: int
    name: str
    start_ticks: int
    service: str


class ProcessController(Protocol):
    def inspect(self, pid: int) -> ProcessIdentity | None: ...

    def terminate(self, pid: int) -> None: ...


class ServiceRestorer(Protocol):
    def restore(self, service: str) -> bool: ...


class ProcfsProcessController:
    def inspect(self, pid: int) -> ProcessIdentity | None:
        if pid <= 0:
            return None
        directory = Path("/proc") / str(pid)
        try:
            name = (directory / "comm").read_text(encoding="utf-8", errors="replace").strip()
            fields = (directory / "stat").read_text(encoding="utf-8", errors="replace").split()
            return ProcessIdentity(pid=pid, name=name, start_ticks=int(fields[21]))
        except (OSError, IndexError, ValueError):
            return None

    def terminate(self, pid: int) -> None:
        os.kill(pid, signal.SIGTERM)


class ControlledProcessExecutor:
    def __init__(
        self,
        *,
        managed_processes: dict[str, str],
        approvals: ApprovalTokenManager,
        controller: ProcessController | None = None,
        restorer: ServiceRestorer | None = None,
        wait_seconds: float = 5.0,
    ) -> None:
        self.managed_processes = dict(managed_processes)
        self.approvals = approvals
        self.controller = controller or ProcfsProcessController()
        self.restorer = restorer
        self.wait_seconds = wait_seconds

    def create_candidate(self, pid: int) -> ProcessCandidate:
        self._protect_pid(pid)
        identity = self.controller.inspect(pid)
        if identity is None:
            raise ValueError("PROCESS_NOT_FOUND")
        service = self.managed_processes.get(identity.name)
        if service is None:
            raise ValueError("PROCESS_NOT_MANAGED")
        snapshot = json.dumps(
            {
                "pid": identity.pid,
                "name": identity.name,
                "start_ticks": identity.start_ticks,
                "service": service,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return ProcessCandidate(
            candidate_id=f"process-{hashlib.sha256(snapshot.encode()).hexdigest()[:24]}",
            pid=identity.pid,
            name=identity.name,
            start_ticks=identity.start_ticks,
            service=service,
        )

    def dry_run(self, candidate: ProcessCandidate) -> dict[str, object]:
        self._require_current(candidate)
        return {
            "tool_name": "terminate_process",
            "candidate_id": candidate.candidate_id,
            "pid": candidate.pid,
            "name": candidate.name,
            "service": candidate.service,
            "start_ticks": candidate.start_ticks,
            "risk_level": "L3",
            "requires_approval": True,
            "state_snapshot": "pid, name, start_ticks and managing systemd service",
            "verification": "original process identity no longer exists",
            "rollback": "restart allowlisted managing service",
        }

    def execute(
        self,
        *,
        user_id: str,
        task_id: str,
        candidate: ProcessCandidate,
        approval_token: str,
    ) -> ExecutionResult:
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="terminate_process",
            arguments={"candidate_id": candidate.candidate_id},
        )
        self._require_current(candidate)
        self.controller.terminate(candidate.pid)
        deadline = time.monotonic() + self.wait_seconds
        while time.monotonic() < deadline:
            current = self.controller.inspect(candidate.pid)
            if current is None or current.start_ticks != candidate.start_ticks:
                break
            time.sleep(min(0.05, self.wait_seconds))
        else:
            self._restore(candidate.service)
            raise ValueError("PROCESS_TERMINATION_FAILED_ROLLED_BACK")
        return ExecutionResult(
            change_id=str(uuid.uuid4()),
            tool_name="terminate_process",
            status="SUCCEEDED",
            backup_ref=None,
            verification=(
                f"pid={candidate.pid}; original_start_ticks={candidate.start_ticks}; absent=true; "
                f"managed_service={candidate.service}"
            ),
        )

    def execute_rollback(
        self,
        *,
        user_id: str,
        task_id: str,
        change_id: str,
        service: str,
        approval_token: str,
    ) -> ExecutionResult:
        self.approvals.consume(
            approval_token,
            user_id=user_id,
            task_id=task_id,
            tool_name="rollback_change",
            arguments={"change_id": change_id},
        )
        self._restore(service)
        return ExecutionResult(
            change_id=change_id,
            tool_name="rollback_change",
            status="ROLLED_BACK",
            backup_ref=None,
            verification=f"managed_service={service}; restart_verified=true",
            rollback_status="SUCCEEDED",
        )

    def _require_current(self, candidate: ProcessCandidate) -> None:
        self._protect_pid(candidate.pid)
        current = self.controller.inspect(candidate.pid)
        expected_service = self.managed_processes.get(candidate.name)
        if (
            current is None
            or current.name != candidate.name
            or current.start_ticks != candidate.start_ticks
            or expected_service != candidate.service
        ):
            raise ValueError("PROCESS_CANDIDATE_STALE_OR_UNSAFE")

    def _restore(self, service: str) -> None:
        if self.restorer is None or not self.restorer.restore(service):
            raise ValueError("PROCESS_ROLLBACK_FAILED")

    @staticmethod
    def _protect_pid(pid: int) -> None:
        if pid <= 1 or pid in {os.getpid(), os.getppid()}:
            raise ValueError("PROCESS_PROTECTED")
