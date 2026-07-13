from collections.abc import Mapping
from pathlib import Path

import pytest

from backend.app.executor.controlled import DemoControlledExecutor
from backend.app.guardrails.approval import ApprovalTokenManager


def approved(
    manager: ApprovalTokenManager,
    tool: str,
    arguments: Mapping[str, object],
) -> str:
    return manager.issue("operator", "task", tool, arguments)


def test_safe_cleanup_backup_verify_and_rollback(tmp_path: Path) -> None:
    manager = ApprovalTokenManager(b"x" * 32)
    executor = DemoControlledExecutor(tmp_path, manager)
    log = tmp_path / "old.log"
    log.write_text("demo log", encoding="utf-8")
    arguments = {"candidate_id": executor.register_candidate(log)}
    preview = executor.dry_run("safe_log_cleanup", arguments)
    assert preview["requires_approval"] is True
    result = executor.execute(
        user_id="operator",
        task_id="task",
        tool_name="safe_log_cleanup",
        arguments=arguments,
        approval_token=approved(manager, "safe_log_cleanup", arguments),
    )
    assert result.status == "SUCCEEDED" and not log.exists()
    rolled_back = executor.rollback(result.change_id)
    assert rolled_back.status == "ROLLED_BACK" and log.read_text(encoding="utf-8") == "demo log"


def test_config_update_is_atomic_and_fault_rolls_back(tmp_path: Path) -> None:
    manager = ApprovalTokenManager(b"x" * 32)
    executor = DemoControlledExecutor(tmp_path, manager)
    config = tmp_path / "app.conf"
    config.write_text("old=true", encoding="utf-8")
    arguments: dict[str, object] = {
        "candidate_id": executor.register_candidate(config),
        "content": "new=true",
    }
    result = executor.execute(
        user_id="operator",
        task_id="task",
        tool_name="config_safe_update",
        arguments=arguments,
        approval_token=approved(manager, "config_safe_update", arguments),
        fault="verification",
    )
    assert result.status == "ROLLED_BACK"
    assert config.read_text(encoding="utf-8") == "old=true"


def test_service_process_whitelists_and_token_tamper(tmp_path: Path) -> None:
    manager = ApprovalTokenManager(b"x" * 32)
    executor = DemoControlledExecutor(tmp_path, manager)
    service_args = {"service": "nginx"}
    result = executor.execute(
        user_id="operator",
        task_id="task",
        tool_name="service_restart",
        arguments=service_args,
        approval_token=approved(manager, "service_restart", service_args),
    )
    assert result.status == "SUCCEEDED"
    with pytest.raises(ValueError, match="SERVICE_NOT_ALLOWED"):
        executor.dry_run("service_restart", {"service": "sshd"})
    with pytest.raises(ValueError, match="PROCESS_PROTECTED_OR_MISSING"):
        executor.dry_run("terminate_process", {"pid": 1})
    process_args = {"pid": 4242}
    token = approved(manager, "terminate_process", process_args)
    with pytest.raises(ValueError, match="APPROVAL_SCOPE_MISMATCH"):
        executor.execute(
            user_id="attacker",
            task_id="task",
            tool_name="terminate_process",
            arguments=process_args,
            approval_token=token,
        )


def test_unknown_candidate_and_repeated_token_are_rejected(tmp_path: Path) -> None:
    manager = ApprovalTokenManager(b"x" * 32)
    executor = DemoControlledExecutor(tmp_path, manager)
    with pytest.raises(ValueError, match="CANDIDATE_NOT_FOUND"):
        executor.dry_run("safe_log_cleanup", {"candidate_id": "user-path-is-not-accepted"})
    args = {"service": "nginx"}
    token = approved(manager, "service_restart", args)
    executor.execute(
        user_id="operator",
        task_id="task",
        tool_name="service_restart",
        arguments=args,
        approval_token=token,
    )
    with pytest.raises(ValueError, match="APPROVAL_REPLAYED"):
        executor.execute(
            user_id="operator",
            task_id="task",
            tool_name="service_restart",
            arguments=args,
            approval_token=token,
        )
