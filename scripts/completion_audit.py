from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402
from mcp_server.registry import ToolRegistry  # noqa: E402
from mcp_server.server import mcp  # noqa: E402


def main() -> int:
    errors: list[str] = []
    routes: set[str] = set()
    pending = list(app.routes)
    seen: set[int] = set()
    while pending:
        route = pending.pop()
        if id(route) in seen:
            continue
        seen.add(id(route))
        path = getattr(route, "path", None)
        if isinstance(path, str):
            routes.add(path)
        nested = getattr(route, "routes", None)
        if isinstance(nested, list):
            pending.extend(nested)
        original = getattr(route, "original_router", None)
        original_routes = getattr(original, "routes", None)
        if isinstance(original_routes, list):
            pending.extend(original_routes)
    required_routes = {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/system/overview",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}",
        "/api/v1/tasks/{task_id}/cancel",
        "/api/v1/tasks/{task_id}/events",
        "/api/v1/tasks/{task_id}/stream",
        "/api/v1/approvals",
        "/api/v1/approvals/{approval_id}",
        "/api/v1/mcp/tools",
        "/api/v1/inspections/run",
        "/api/v1/incidents",
        "/api/v1/config-drift",
        "/api/v1/knowledge",
        "/api/v1/audit/events",
        "/api/v1/audit/verify",
        "/api/v1/audit/export",
        "/api/v1/settings",
    }
    for route in sorted(required_routes - routes):
        errors.append(f"required API route missing: {route}")

    tools = ToolRegistry.for_mode("READ_ONLY").list_tools()
    if len(tools) != 14 or not all(tool.read_only for tool in tools):
        errors.append("read-only Tool registry must contain exactly 14 read-only tools")
    sdk_tools = asyncio.run(mcp.list_tools())
    if len(sdk_tools) != 14:
        errors.append("FastMCP SDK registry does not expose 14 tools")

    source_checkout = (ROOT / "frontend/src").is_dir()
    required_files = (
        "backend/app/guardrails/policy.py",
        "backend/app/guardrails/approval.py",
        "backend/app/agent/runners.py",
        "backend/app/agent/rca.py",
        "backend/app/executor/controlled.py",
        "backend/app/core/trends.py",
        "backend/app/core/config_drift.py",
        "deploy/install.sh",
        "deploy/uninstall.sh",
        "deploy/healthcheck.sh",
        "deploy/kylin-guard.service",
        "deploy/nginx.conf",
        "deploy/kylin-guard.sudoers",
    )
    for relative in required_files:
        if not (ROOT / relative).is_file():
            errors.append(f"required artifact missing: {relative}")

    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "backend").rglob("*.py")
    )
    for symbol in (
        "ReActRunner",
        "PlanAndExecuteRunner",
        "EvidenceManager",
        "ResponseComposer",
        "ApprovalTokenManager",
        "DemoControlledExecutor",
        "verify_chain",
        "PeriodicSnapshotService",
    ):
        if symbol not in source:
            errors.append(f"required implementation symbol missing: {symbol}")

    if source_checkout:
        if not (ROOT / "data/performance-current-host.json").is_file():
            errors.append("required artifact missing: data/performance-current-host.json")
        frontend = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "frontend/src").rglob("*")
            if path.is_file()
        )
        for marker in (
            "安全审批中心",
            "MCP 工具中心",
            "故障事件与根因分析",
            "配置漂移",
            "审计日志",
            "echarts/core",
        ):
            if marker not in frontend:
                errors.append(f"frontend capability missing: {marker}")
    else:
        if not (ROOT / "frontend/dist/index.html").is_file():
            errors.append("production frontend index is missing")
        if not list((ROOT / "frontend/dist/assets").glob("*.js")):
            errors.append("production frontend assets are missing")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Phase 2-9 completion audit passed for current-host-verifiable requirements.")
    print("Kylin V11 and LoongArch runtime verification remains explicitly external.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
