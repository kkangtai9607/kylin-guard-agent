import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.agent.cleanup import (
    CleanupCandidateClassifier,
    CleanupPolicy,
    FileUseState,
)


def classifier(root: Path, protected: Path | None = None) -> CleanupCandidateClassifier:
    return CleanupCandidateClassifier(
        CleanupPolicy(
            allowed_roots=(root,),
            protected_paths=(protected,) if protected else (),
            minimum_age_days=7,
            minimum_size_bytes=8,
        )
    )


def old_file(path: Path, content: str = "old log data") -> None:
    path.write_text(content, encoding="utf-8")
    timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_safe_old_closed_log_becomes_frozen_candidate(tmp_path: Path) -> None:
    target = tmp_path / "application.log"
    old_file(target)
    decision = classifier(tmp_path).classify(str(target), use_state=FileUseState.NOT_OPEN)
    assert decision.eligible is True
    assert decision.candidate is not None
    assert decision.candidate.candidate_id.startswith("cleanup-")
    assert decision.candidate.requires_approval is True
    assert classifier(tmp_path).revalidate(
        decision.candidate, use_state=FileUseState.NOT_OPEN
    ) is True


def test_open_or_unknown_file_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / "application.log"
    old_file(target)
    for state, reason in (
        (FileUseState.OPEN, "FILE_IS_OPEN"),
        (FileUseState.UNKNOWN, "OPEN_FILE_STATE_UNKNOWN"),
    ):
        decision = classifier(tmp_path).classify(str(target), use_state=state)
        assert decision.eligible is False
        assert reason in decision.reason_codes


def test_database_and_audit_logs_are_never_candidates(tmp_path: Path) -> None:
    for name in ("mysql-bin.log", "security-audit.log", "postgresql.old"):
        target = tmp_path / name
        old_file(target)
        decision = classifier(tmp_path).classify(str(target), use_state=FileUseState.NOT_OPEN)
        assert decision.eligible is False
        assert "CRITICAL_OR_DATABASE_LOG" in decision.reason_codes


def test_candidate_invalid_after_file_changes(tmp_path: Path) -> None:
    target = tmp_path / "application.log"
    old_file(target)
    decision = classifier(tmp_path).classify(str(target), use_state=FileUseState.NOT_OPEN)
    assert decision.candidate is not None
    target.write_text("changed log payload", encoding="utf-8")
    assert classifier(tmp_path).revalidate(
        decision.candidate, use_state=FileUseState.NOT_OPEN
    ) is False


def test_protected_path_and_symlink_are_rejected(tmp_path: Path) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    target = protected / "application.log"
    old_file(target)
    decision = classifier(tmp_path, protected).classify(
        str(target), use_state=FileUseState.NOT_OPEN
    )
    assert decision.eligible is False
    assert "PROTECTED_PATH" in decision.reason_codes

    link = tmp_path / "linked.log"
    try:
        link.symlink_to(target)
    except OSError:
        return
    linked = classifier(tmp_path).classify(str(link), use_state=FileUseState.NOT_OPEN)
    assert linked.eligible is False
