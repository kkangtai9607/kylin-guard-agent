import os

import pytest

from backend.app.executor.process import (
    ControlledProcessExecutor,
    ProcessIdentity,
)
from backend.app.guardrails.approval import ApprovalTokenManager


class FakeController:
    def __init__(self, identity: ProcessIdentity | None) -> None:
        self.identity = identity
        self.terminated: list[int] = []
        self.keep_alive = False

    def inspect(self, pid: int) -> ProcessIdentity | None:
        return self.identity if self.identity is not None and self.identity.pid == pid else None

    def terminate(self, pid: int) -> None:
        self.terminated.append(pid)
        if not self.keep_alive:
            self.identity = None


class FakeRestorer:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.services: list[str] = []

    def restore(self, service: str) -> bool:
        self.services.append(service)
        return self.succeeds


def setup_executor(
    controller: FakeController, restorer: FakeRestorer | None = None
) -> tuple[ControlledProcessExecutor, ApprovalTokenManager]:
    approvals = ApprovalTokenManager(b"t" * 32)
    return (
        ControlledProcessExecutor(
            managed_processes={"nginx": "nginx"},
            approvals=approvals,
            controller=controller,
            restorer=restorer or FakeRestorer(),
            wait_seconds=0.01,
        ),
        approvals,
    )


def test_managed_process_candidate_binds_start_time_and_executes() -> None:
    controller = FakeController(ProcessIdentity(4242, "nginx", 998877))
    executor, approvals = setup_executor(controller)
    candidate = executor.create_candidate(4242)
    assert candidate.candidate_id.startswith("process-")
    assert executor.dry_run(candidate)["requires_approval"] is True
    token = approvals.issue(
        "operator", "task", "terminate_process", {"candidate_id": candidate.candidate_id}
    )
    result = executor.execute(
        user_id="operator",
        task_id="task",
        candidate=candidate,
        approval_token=token,
    )
    assert result.status == "SUCCEEDED"
    assert controller.terminated == [4242]


def test_pid_reuse_or_name_change_invalidates_candidate() -> None:
    controller = FakeController(ProcessIdentity(4242, "nginx", 100))
    executor, approvals = setup_executor(controller)
    candidate = executor.create_candidate(4242)
    controller.identity = ProcessIdentity(4242, "nginx", 101)
    token = approvals.issue(
        "operator", "task", "terminate_process", {"candidate_id": candidate.candidate_id}
    )
    with pytest.raises(ValueError, match="PROCESS_CANDIDATE_STALE_OR_UNSAFE"):
        executor.execute(
            user_id="operator",
            task_id="task",
            candidate=candidate,
            approval_token=token,
        )
    assert controller.terminated == []


def test_unmanaged_and_critical_processes_are_rejected() -> None:
    unmanaged = FakeController(ProcessIdentity(4242, "postgres", 100))
    executor, _ = setup_executor(unmanaged)
    with pytest.raises(ValueError, match="PROCESS_NOT_MANAGED"):
        executor.create_candidate(4242)
    for pid in {0, 1, os.getpid(), os.getppid()}:
        with pytest.raises(ValueError, match="PROCESS_PROTECTED"):
            executor.create_candidate(pid)


def test_failed_termination_uses_managing_service_for_restore() -> None:
    controller = FakeController(ProcessIdentity(4242, "nginx", 100))
    controller.keep_alive = True
    restorer = FakeRestorer()
    executor, approvals = setup_executor(controller, restorer)
    candidate = executor.create_candidate(4242)
    token = approvals.issue(
        "operator", "task", "terminate_process", {"candidate_id": candidate.candidate_id}
    )
    with pytest.raises(ValueError, match="PROCESS_TERMINATION_FAILED_ROLLED_BACK"):
        executor.execute(
            user_id="operator",
            task_id="task",
            candidate=candidate,
            approval_token=token,
        )
    assert restorer.services == ["nginx"]


def test_process_rollback_requires_separate_bound_approval() -> None:
    restorer = FakeRestorer()
    executor, approvals = setup_executor(FakeController(None), restorer)
    token = approvals.issue("operator", "task", "rollback_change", {"change_id": "change-1"})
    result = executor.execute_rollback(
        user_id="operator",
        task_id="task",
        change_id="change-1",
        service="nginx",
        approval_token=token,
    )
    assert result.status == "ROLLED_BACK"
    assert restorer.services == ["nginx"]
