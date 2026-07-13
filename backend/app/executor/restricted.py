from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DryRunResult:
    tool_name: str
    impact_summary: str
    requires_backup: bool
    verification: str
    rollback: str


class HarmlessAdapter(Protocol):
    def dry_run(self, tool_name: str, arguments: dict[str, object]) -> DryRunResult: ...


class RestrictedExecutor:
    """Phase 3 framework: only dry-run adapters are accepted; no real mutation exists."""

    def __init__(self, adapter: HarmlessAdapter) -> None:
        self.adapter = adapter

    def preview(self, tool_name: str, arguments: dict[str, object]) -> DryRunResult:
        return self.adapter.dry_run(tool_name, arguments)


class DemoDryRunAdapter:
    def dry_run(self, tool_name: str, arguments: dict[str, object]) -> DryRunResult:
        return DryRunResult(
            tool_name,
            f"DEMO preview for {tool_name}: {sorted(arguments)}",
            True,
            "demo verification",
            "demo rollback",
        )
