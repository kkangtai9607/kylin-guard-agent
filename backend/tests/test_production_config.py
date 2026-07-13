from pathlib import Path

import pytest

from backend.app.executor.config_update import (
    ConfigTarget,
    ControlledConfigExecutor,
)
from backend.app.guardrails.approval import ApprovalTokenManager


class FakeValidator:
    def __init__(self, results: list[bool] | None = None) -> None:
        self.results = results or [True, True]
        self.calls: list[Path] = []

    def validate(self, target: ConfigTarget, candidate: Path) -> bool:
        self.calls.append(candidate)
        return self.results.pop(0)


def setup_executor(
    tmp_path: Path, validator: FakeValidator
) -> tuple[ControlledConfigExecutor, ApprovalTokenManager, Path]:
    config = tmp_path / "nginx.conf"
    config.write_text("events {}\nhttp {}\n", encoding="utf-8")
    approvals = ApprovalTokenManager(b"c" * 32)
    executor = ControlledConfigExecutor(
        targets=(
            ConfigTarget(
                target_id="nginx-main",
                path=config,
                validator="nginx",
                validator_path=Path("/usr/sbin/nginx"),
            ),
        ),
        backup_root=tmp_path / "backups",
        approvals=approvals,
        validator=validator,
    )
    return executor, approvals, config


def test_config_update_validates_backs_up_and_atomically_replaces(tmp_path: Path) -> None:
    validator = FakeValidator()
    executor, approvals, config = setup_executor(tmp_path, validator)
    content = "events { worker_connections 512; }\nhttp {}\n"
    preview = executor.dry_run("nginx-main", content)
    assert preview["requires_approval"] is True
    token = approvals.issue(
        "operator",
        "task",
        "config_safe_update",
        {"target_id": "nginx-main", "content": content},
    )
    result = executor.execute(
        user_id="operator",
        task_id="task",
        target_id="nginx-main",
        content=content,
        approval_token=token,
    )
    assert result.status == "SUCCEEDED"
    assert config.read_text(encoding="utf-8") == content
    assert result.backup_ref is not None and Path(result.backup_ref).is_file()
    assert len(validator.calls) == 2


def test_invalid_candidate_never_replaces_original(tmp_path: Path) -> None:
    validator = FakeValidator([False])
    executor, approvals, config = setup_executor(tmp_path, validator)
    original = config.read_text(encoding="utf-8")
    content = "invalid config\n"
    token = approvals.issue(
        "operator",
        "task",
        "config_safe_update",
        {"target_id": "nginx-main", "content": content},
    )
    with pytest.raises(ValueError, match="CONFIG_VALIDATION_FAILED"):
        executor.execute(
            user_id="operator",
            task_id="task",
            target_id="nginx-main",
            content=content,
            approval_token=token,
        )
    assert config.read_text(encoding="utf-8") == original


def test_post_replace_failure_restores_verified_backup(tmp_path: Path) -> None:
    validator = FakeValidator([True, False])
    executor, approvals, config = setup_executor(tmp_path, validator)
    original = config.read_text(encoding="utf-8")
    content = "events {}\nhttp { server { listen 8080; } }\n"
    token = approvals.issue(
        "operator",
        "task",
        "config_safe_update",
        {"target_id": "nginx-main", "content": content},
    )
    with pytest.raises(ValueError, match="POSTCONDITION_FAILED"):
        executor.execute(
            user_id="operator",
            task_id="task",
            target_id="nginx-main",
            content=content,
            approval_token=token,
        )
    assert config.read_text(encoding="utf-8") == original


def test_arbitrary_target_and_unchanged_content_are_rejected(tmp_path: Path) -> None:
    executor, _, config = setup_executor(tmp_path, FakeValidator())
    with pytest.raises(ValueError, match="CONFIG_TARGET_NOT_ALLOWED"):
        executor.dry_run("user-supplied-path", "content")
    with pytest.raises(ValueError, match="CONFIG_UNCHANGED"):
        executor.dry_run("nginx-main", config.read_text(encoding="utf-8"))
