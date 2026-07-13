from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.agent.planning import Planner  # noqa: E402
from backend.app.llm.provider import provider_from_environment  # noqa: E402
from backend.app.mcp_client.client import KylinGuardMCPClient  # noqa: E402
from mcp_server.registry import ToolRegistry  # noqa: E402


def main() -> int:
    goal = "分析当前项目所在磁盘的空间使用情况，只做只读诊断"
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(provider_from_environment(), mcp).plan(goal)
    tools = [step.tool_name for step in plan.steps]
    if "disk_usage_scan" not in tools:
        raise RuntimeError("DeepSeek plan omitted deterministic disk evidence tool")
    print(
        json.dumps(
            {
                "goal_exact": plan.user_goal == goal,
                "intent": plan.intent,
                "risk_level": plan.risk_level,
                "requires_approval": plan.requires_approval,
                "tools": tools,
                "summary": plan.summary,
                "public_reason": plan.public_reason,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
