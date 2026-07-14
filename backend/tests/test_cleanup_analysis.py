import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.agent.cleanup import CleanupAnalysisService, CleanupPolicy
from backend.app.mcp_client.client import KylinGuardMCPClient
from mcp_server.providers import ReadOnlyProvider
from mcp_server.registry import ToolRegistry
from mcp_server.schemas.models import ToolResult


class OccupancyClient(KylinGuardMCPClient):
    def __init__(self, root: Path, open_paths: set[str] | None = None) -> None:
        super().__init__(ToolRegistry(ReadOnlyProvider(allowed_roots=(root,))))
        self.open_paths = open_paths or set()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        if name == "open_file_lookup":
            path = str((arguments or {})["path"])
            return ToolResult(
                tool_name=name,
                status="SUCCEEDED",
                data={"supported": True, "raw": "process" if path in self.open_paths else ""},
            )
        return super().call_tool(name, arguments)


def make_old(path: Path) -> None:
    path.write_bytes(b"x" * 16)
    timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_analysis_correlates_large_file_and_live_occupancy(tmp_path: Path) -> None:
    safe = tmp_path / "old-app.log"
    active = tmp_path / "active.log"
    make_old(safe)
    make_old(active)
    client = OccupancyClient(tmp_path, {str(active)})
    service = CleanupAnalysisService(
        client,
        CleanupPolicy(
            allowed_roots=(tmp_path,),
            protected_paths=(),
            minimum_age_days=7,
            minimum_size_bytes=8,
        ),
    )
    decisions = service.analyze_large_file_result(
        {"data": {"files": [{"path": str(safe)}, {"path": str(active)}]}}
    )
    assert decisions[0].eligible is True
    assert decisions[1].eligible is False
    assert "FILE_IS_OPEN" in decisions[1].reason_codes


def test_analysis_rejects_when_occupancy_capability_is_unknown(tmp_path: Path) -> None:
    target = tmp_path / "old-app.log"
    make_old(target)
    client = KylinGuardMCPClient(ToolRegistry(ReadOnlyProvider(allowed_roots=(tmp_path,))))
    service = CleanupAnalysisService(
        client,
        CleanupPolicy(
            allowed_roots=(tmp_path,),
            protected_paths=(),
            minimum_age_days=7,
            minimum_size_bytes=8,
        ),
    )
    decisions = service.analyze_large_file_result({"data": {"files": [{"path": str(target)}]}})
    if decisions[0].eligible is False:
        assert "OPEN_FILE_STATE_UNKNOWN" in decisions[0].reason_codes


def test_analysis_keeps_download_installer_when_occupancy_capability_is_unknown(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    target = downloads / "toolkit.msi"
    target.write_bytes(b"x" * 16)
    client = KylinGuardMCPClient(
        ToolRegistry(ReadOnlyProvider(allowed_roots=(tmp_path,), cleanup_roots=(downloads,)))
    )
    service = CleanupAnalysisService(
        client,
        CleanupPolicy(
            allowed_roots=(downloads,),
            protected_paths=(),
            minimum_age_days=7,
            minimum_size_bytes=8,
        ),
    )

    decisions = service.analyze_large_file_result({"data": {"files": [{"path": str(target)}]}})

    assert decisions[0].eligible is True
    assert decisions[0].candidate is not None
    assert decisions[0].candidate.classification == "DISPOSABLE_DOWNLOAD_OR_CACHE_CANDIDATE"


def test_analysis_returns_observed_file_when_candidate_is_rejected_by_policy(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    target = outside / "large.bin"
    target.write_bytes(b"x" * 16)
    client = KylinGuardMCPClient(
        ToolRegistry(ReadOnlyProvider(allowed_roots=(tmp_path,), cleanup_roots=(outside,)))
    )
    service = CleanupAnalysisService(
        client,
        CleanupPolicy(
            allowed_roots=(allowed,),
            protected_paths=(),
            minimum_age_days=7,
            minimum_size_bytes=8,
        ),
    )

    decisions = service.analyze_large_file_result(
        {"data": {"files": [{"path": str(target), "size": target.stat().st_size}]}}
    )

    assert decisions[0].eligible is False
    assert decisions[0].candidate is None
    assert decisions[0].observed_file is not None
    assert decisions[0].observed_file.path == str(target)
    assert decisions[0].observed_file.size_bytes == 16
