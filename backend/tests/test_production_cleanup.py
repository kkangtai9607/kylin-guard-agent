import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.agent.cleanup import (
    CleanupCandidate,
    CleanupCandidateClassifier,
    CleanupPolicy,
    FileUseState,
)
from backend.app.executor.production import ControlledCleanupExecutor
from backend.app.guardrails.approval import ApprovalTokenManager


def setup_candidate(tmp_path: Path) -> tuple[Path, CleanupCandidate, CleanupPolicy]:
    managed = tmp_path / "managed"
    managed.mkdir()
    target = managed / "old-app.log"
    target.write_bytes(b"old application log\n" * 100)
    timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(target, (timestamp, timestamp))
    policy = CleanupPolicy(
        allowed_roots=(managed,),
        protected_paths=(),
        minimum_age_days=7,
        minimum_size_bytes=8,
    )
    decision = CleanupCandidateClassifier(policy).classify(
        str(target), use_state=FileUseState.NOT_OPEN
    )
    assert decision.candidate is not None
    return target, decision.candidate, policy


def executor_and_token(
    tmp_path: Path, candidate: CleanupCandidate, policy: CleanupPolicy
) -> tuple[ControlledCleanupExecutor, str]:
    manager = ApprovalTokenManager(b"p" * 32)
    executor = ControlledCleanupExecutor(
        policy=policy,
        backup_root=tmp_path / "backups",
        approvals=manager,
    )
    token = manager.issue(
        "operator", "task", "safe_log_cleanup", {"candidate_id": candidate.candidate_id}
    )
    return executor, token


def test_controlled_cleanup_archives_deletes_and_can_rollback(tmp_path: Path) -> None:
    target, candidate, policy = setup_candidate(tmp_path)
    executor, token = executor_and_token(tmp_path, candidate, policy)
    preview = executor.dry_run(candidate, use_state=FileUseState.NOT_OPEN)
    assert preview["requires_approval"] is True
    result = executor.execute(
        user_id="operator",
        task_id="task",
        candidate=candidate,
        approval_token=token,
        use_state=FileUseState.NOT_OPEN,
    )
    assert result.status == "SUCCEEDED"
    assert not target.exists()
    assert result.backup_ref is not None
    rollback_token = executor.approvals.issue(
        "operator", "task", "rollback_change", {"change_id": result.change_id}
    )
    rolled_back = executor.execute_rollback(
        user_id="operator",
        task_id="task",
        change_id=result.change_id,
        backup_ref=result.backup_ref,
        target_path=str(target),
        approval_token=rollback_token,
    )
    assert rolled_back.status == "ROLLED_BACK"
    assert target.read_bytes().startswith(b"old application log")


def test_controlled_cleanup_rechecks_stale_and_open_candidate(tmp_path: Path) -> None:
    target, candidate, policy = setup_candidate(tmp_path)
    executor, token = executor_and_token(tmp_path, candidate, policy)
    with pytest.raises(ValueError, match="CANDIDATE_STALE_OR_UNSAFE"):
        executor.execute(
            user_id="operator",
            task_id="task",
            candidate=candidate,
            approval_token=token,
            use_state=FileUseState.OPEN,
        )
    target.write_bytes(b"changed after approval")
    executor, token = executor_and_token(tmp_path, candidate, policy)
    with pytest.raises(ValueError, match="CANDIDATE_STALE_OR_UNSAFE"):
        executor.execute(
            user_id="operator",
            task_id="task",
            candidate=candidate,
            approval_token=token,
            use_state=FileUseState.NOT_OPEN,
        )


def test_verification_failure_restores_original(tmp_path: Path) -> None:
    target, candidate, policy = setup_candidate(tmp_path)
    original = target.read_bytes()
    executor, token = executor_and_token(tmp_path, candidate, policy)
    with pytest.raises(ValueError, match="POSTCONDITION_FAILED"):
        executor.execute(
            user_id="operator",
            task_id="task",
            candidate=candidate,
            approval_token=token,
            use_state=FileUseState.NOT_OPEN,
            simulate_verification_failure=True,
        )
    assert target.read_bytes() == original
