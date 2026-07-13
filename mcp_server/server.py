from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.registry import ToolRegistry

mcp = FastMCP("KylinGuard Read-Only MCP", json_response=True)
registry = ToolRegistry.for_mode("READ_ONLY")


def _create_invoke(tool_name: str) -> Any:
    def invoke(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke a registered read-only KylinGuard tool."""
        return registry.call(tool_name, arguments).model_dump(mode="json")

    return invoke


def _register_tools() -> None:
    for metadata in registry.list_tools():
        name = metadata.name
        invoke = _create_invoke(name)

        invoke.__name__ = name
        invoke.__doc__ = metadata.description_zh
        mcp.tool(name=name, description=metadata.description_zh)(invoke)


_register_tools()


if __name__ == "__main__":
    mcp.run(transport="stdio")
