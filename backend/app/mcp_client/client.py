from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.core.config import get_config
from mcp_server.registry import ToolRegistry
from mcp_server.schemas.models import ToolMetadata, ToolResult


class KylinGuardMCPClient:
    """Backend adapter; transport-backed sessions can replace the in-process registry."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        config = get_config()
        self.registry = registry or ToolRegistry.for_mode(
            config.mode,
            allowed_roots=config.read_only_scan_roots(),
            cleanup_roots=config.controlled_cleanup_roots(),
        )

    def health(self) -> dict[str, Any]:
        result = self.registry.call("capability_probe")
        return {
            "status": "ok" if result.status == "SUCCEEDED" else "degraded",
            "tool_count": len(self.registry.list_tools()),
        }

    def list_tools(self) -> list[ToolMetadata]:
        return self.registry.list_tools()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        return self.registry.call(name, arguments)

    def allowed_roots(self) -> tuple[Path, ...]:
        """Expose the provider's normalized read scope, never a caller-supplied path."""
        return self.registry.provider.allowed_roots

    def cleanup_roots(self) -> tuple[Path, ...]:
        """Expose the provider's controlled cleanup candidate scope."""
        return self.registry.provider.cleanup_roots
