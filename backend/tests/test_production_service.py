from pathlib import Path

import pytest

from backend.app.executor.systemd import (
    CommandOutcome,
    ControlledServiceExecutor,
)
from backend.app.guardrails.approval import ApprovalTokenManager


class FakeSystemctlRunner:
    def __init__(self, *, fail_restart: bool = False, fail_rollback: bool = False) -> None:
        self.active = True
        self.fail_restart = fail_restart
        self.fail_rollback = fail_rollback
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...], *, timeout: int) -> CommandOutcome:
        self.calls.append(argv)
        action = argv[1]
        if action == "is-active":
            return CommandOutcome(0 if self.active else 3, "active\n" if self.active else "inactive\n")
        if action == "restart" and self.fail_restart:
            self.active = False
            return CommandOutcome(1, stderr="restart failed")
        if action == "start" and self.fail_rollback:
            return CommandOutcome(1, stderr="start failed")
        if action in {"restart", "start"}:
            self.active = True
        return CommandOutcome(0)


def make_executor(runner: FakeSystemctlRunner) -> tuple[ControlledServiceExecutor, ApprovalTokenManager]:
    approvals = ApprovalTokenManager(b"s" * 32)
    return (
        ControlledServiceExecutor(
            executable=Path("/usr/bin/systemctl"),
            allowed_services=("nginx",),
            approvals=approvals,
            runner=runner,
        ),
        approvals,
    )


def test_service_restart_uses_only_fixed_argv_and_verifies() -> None:
    runner = FakeSystemctlRunner()
    executor, approvals = make_executor(runner)
    preview = executor.dry_run("nginx")
    assert preview["requires_approval"] is True
    token = approvals.issue("operator", "task", "service_restart", {"service": "nginx"})
    result = executor.execute(
        user_id="operator",
        task_id="task",
        service="nginx",
        approval_token=token,
    )
    assert result.status == "SUCCEEDED"
    assert any(call[1:] == ("restart", "nginx") for call in runner.calls)


@pytest.mark.parametrize("service", ["sshd", "nginx --now", "nginx\nstop"])
def test_service_name_outside_exact_allowlist_is_rejected(service: str) -> None:
    executor, _ = make_executor(FakeSystemctlRunner())
    with pytest.raises(ValueError, match="SERVICE_NOT_ALLOWED|SERVICE_NAME_INVALID"):
        executor.dry_run(service)


def test_failed_restart_restores_previous_active_state() -> None:
    runner = FakeSystemctlRunner(fail_restart=True)
    executor, approvals = make_executor(runner)
    token = approvals.issue("operator", "task", "service_restart", {"service": "nginx"})
    with pytest.raises(ValueError, match="SERVICE_RESTART_FAILED_ROLLED_BACK"):
        executor.execute(
            user_id="operator",
            task_id="task",
            service="nginx",
            approval_token=token,
        )
    assert runner.active is True
    assert any(call[1:] == ("start", "nginx") for call in runner.calls)


def test_failed_restart_and_restore_fails_closed() -> None:
    runner = FakeSystemctlRunner(fail_restart=True, fail_rollback=True)
    executor, approvals = make_executor(runner)
    token = approvals.issue("operator", "task", "service_restart", {"service": "nginx"})
    with pytest.raises(ValueError, match="SERVICE_RESTART_AND_ROLLBACK_FAILED"):
        executor.execute(
            user_id="operator",
            task_id="task",
            service="nginx",
            approval_token=token,
        )


def test_service_rollback_requires_separate_approval() -> None:
    runner = FakeSystemctlRunner()
    executor, approvals = make_executor(runner)
    token = approvals.issue("operator", "task", "rollback_change", {"change_id": "change-1"})
    result = executor.execute_rollback(
        user_id="operator",
        task_id="task",
        change_id="change-1",
        service="nginx",
        approval_token=token,
    )
    assert result.status == "ROLLED_BACK"
    assert any(call[1:] == ("restart", "nginx") for call in runner.calls)
