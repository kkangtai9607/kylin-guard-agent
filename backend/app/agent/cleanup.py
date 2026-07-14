from __future__ import annotations

import hashlib
import json
import stat
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from backend.app.guardrails.policy import PathGuard
from backend.app.mcp_client.client import KylinGuardMCPClient


class FileUseState(str, Enum):
    NOT_OPEN = "NOT_OPEN"
    OPEN = "OPEN"
    UNKNOWN = "UNKNOWN"


class CleanupPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_roots: tuple[Path, ...]
    protected_paths: tuple[Path, ...]
    minimum_age_days: int = Field(default=7, ge=1, le=3650)
    minimum_size_bytes: int = Field(default=10_000_000, ge=1)
    allowed_suffixes: tuple[str, ...] = (
        ".log",
        ".gz",
        ".old",
        ".tmp",
        ".cache",
        ".msi",
        ".iso",
        ".zip",
        ".tar",
        ".tgz",
        ".tar.gz",
        ".7z",
        ".rar",
        ".rpm",
        ".deb",
        ".apk",
        ".dmg",
        ".pkg",
        ".exe",
    )
    low_risk_dir_names: tuple[str, ...] = (
        ".cache",
        "cache",
        "downloads",
        "download",
        "tmp",
        "temp",
    )
    forbidden_name_terms: tuple[str, ...] = (
        "audit",
        "journal",
        "mysql-bin",
        "binlog",
        "postgresql",
        "transaction",
        "redo",
        "wal",
        "secret",
        "token",
        "password",
        "credential",
        "private-key",
        "id_rsa",
    )


class CleanupCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    path: str
    size_bytes: int
    modified_at: datetime
    inode: int
    device: int
    snapshot_hash: str
    classification: str = "SAFE_LOG_OR_CACHE_CANDIDATE"
    risk_level: str = "L3"
    requires_approval: bool = True


class CleanupDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eligible: bool
    reason_codes: list[str]
    candidate: CleanupCandidate | None = None


class CleanupCandidateClassifier:
    """确定性清理候选分类器；不调用模型，也不执行任何状态变更。"""

    def __init__(self, policy: CleanupPolicy) -> None:
        self.policy = policy
        self.path_guard = PathGuard(policy.allowed_roots, policy.protected_paths)

    def classify(
        self,
        raw_path: str,
        *,
        use_state: FileUseState,
        now: datetime | None = None,
    ) -> CleanupDecision:
        reasons: list[str] = []
        try:
            target = self.path_guard.validate(raw_path)
        except (OSError, ValueError) as error:
            return CleanupDecision(eligible=False, reason_codes=[str(error)])

        try:
            metadata = target.stat(follow_symlinks=False)
        except OSError:
            return CleanupDecision(eligible=False, reason_codes=["STAT_FAILED"])

        if not stat.S_ISREG(metadata.st_mode):
            reasons.append("NOT_REGULAR_FILE")
        if not self._suffix_allowed(target):
            reasons.append("FILE_TYPE_NOT_ALLOWED")
        lowered = target.name.lower()
        if any(term in lowered for term in self.policy.forbidden_name_terms):
            reasons.append("CRITICAL_OR_DATABASE_LOG")
        if metadata.st_size < self.policy.minimum_size_bytes:
            reasons.append("BELOW_SIZE_THRESHOLD")

        reference = now or datetime.now(timezone.utc)
        modified = datetime.fromtimestamp(metadata.st_mtime, timezone.utc)
        age_seconds = (reference - modified).total_seconds()
        low_risk_disposable = self._is_low_risk_disposable(target)
        if not low_risk_disposable and age_seconds < self.policy.minimum_age_days * 86400:
            reasons.append("RETENTION_PERIOD_NOT_MET")
        if use_state == FileUseState.OPEN:
            reasons.append("FILE_IS_OPEN")
        elif use_state == FileUseState.UNKNOWN:
            reasons.append("OPEN_FILE_STATE_UNKNOWN")
        if reasons:
            return CleanupDecision(eligible=False, reason_codes=reasons)

        snapshot = {
            "path": str(target),
            "size": metadata.st_size,
            "mtime_ns": metadata.st_mtime_ns,
            "inode": metadata.st_ino,
            "device": metadata.st_dev,
        }
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        snapshot_hash = hashlib.sha256(canonical.encode()).hexdigest()
        candidate_id = f"cleanup-{snapshot_hash[:24]}"
        return CleanupDecision(
            eligible=True,
            reason_codes=["SAFE_CANDIDATE"],
            candidate=CleanupCandidate(
                candidate_id=candidate_id,
                path=str(target),
                size_bytes=metadata.st_size,
                modified_at=modified,
                inode=metadata.st_ino,
                device=metadata.st_dev,
                snapshot_hash=snapshot_hash,
                classification=(
                    "DISPOSABLE_DOWNLOAD_OR_CACHE_CANDIDATE"
                    if low_risk_disposable
                    else "SAFE_LOG_OR_CACHE_CANDIDATE"
                ),
            ),
        )

    def _suffix_allowed(self, target: Path) -> bool:
        lowered = target.name.lower()
        return any(lowered.endswith(suffix) for suffix in self.policy.allowed_suffixes)

    def _is_low_risk_disposable(self, target: Path) -> bool:
        parents = [target.parent, *target.parents]
        return any(parent.name.lower() in self.policy.low_risk_dir_names for parent in parents)

    def revalidate(self, candidate: CleanupCandidate, *, use_state: FileUseState) -> bool:
        decision = self.classify(candidate.path, use_state=use_state)
        return bool(
            decision.eligible
            and decision.candidate is not None
            and decision.candidate.snapshot_hash == candidate.snapshot_hash
        )


class CleanupAnalysisService:
    """Correlate large-file evidence with live open-file checks, failing closed."""

    def __init__(self, mcp: KylinGuardMCPClient, policy: CleanupPolicy | None = None) -> None:
        self.mcp = mcp
        roots = mcp.cleanup_roots()
        self.classifier = CleanupCandidateClassifier(
            policy
            or CleanupPolicy(
                allowed_roots=roots,
                protected_paths=tuple(
                    path
                    for path in (Path("/etc"), Path("/root"), Path("/boot"), Path("/proc"))
                    if path.exists()
                ),
            )
        )

    def analyze_large_file_result(self, payload: dict[str, object]) -> list[CleanupDecision]:
        raw_data = payload.get("data")
        if not isinstance(raw_data, dict):
            return []
        raw_files = raw_data.get("files")
        if not isinstance(raw_files, list):
            return []
        decisions: list[CleanupDecision] = []
        for item in raw_files[:100]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            path = item["path"]
            occupancy = self.mcp.call_tool("open_file_lookup", {"path": path})
            state = FileUseState.UNKNOWN
            if occupancy.status == "SUCCEEDED" and occupancy.data.get("supported") is True:
                state = FileUseState.OPEN if str(occupancy.data.get("raw", "")).strip() else FileUseState.NOT_OPEN
            decisions.append(self.classifier.classify(path, use_state=state))
        return decisions
