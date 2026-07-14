from __future__ import annotations

import re
import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.guardrails.policy import PolicyEngine
from backend.app.llm.provider import LLMProvider, LLMUnavailableError
from backend.app.mcp_client.client import KylinGuardMCPClient


class Intent(str, Enum):
    QUERY = "QUERY"
    DIAGNOSIS = "DIAGNOSIS"
    INSPECTION = "INSPECTION"
    CHANGE = "CHANGE"
    CLEANUP = "CLEANUP"
    RECOVERY = "RECOVERY"
    FORBIDDEN = "FORBIDDEN"


class Complexity(str, Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1, le=20)
    tool_name: str
    arguments: dict[str, object] = {}
    purpose: str = Field(max_length=500)


class ActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str
    user_goal: str
    intent: Intent
    complexity: Complexity
    summary: str
    steps: list[PlanStep] = Field(max_length=20)
    expected_evidence: list[str]
    risk_level: Literal["L0", "L1", "L2", "L3", "L4"]
    requires_approval: bool
    verification: str
    rollback: str
    public_reason: str


# Keep Chinese keywords as unicode escapes so Windows console/codepage issues cannot
# corrupt routing logic again.
DISK_TERMS = (
    "\u78c1\u76d8",  # 磁盘
    "\u786c\u76d8",  # 硬盘
    "\u7a7a\u95f4",  # 空间
    "\u5bb9\u91cf",  # 容量
    "disk",
    "filesystem usage",
)
CLEANUP_TERMS = (
    "\u6e05\u7406",  # 清理
    "\u5783\u573e",  # 垃圾
    "\u65e7\u65e5\u5fd7",  # 旧日志
    "\u7f13\u5b58",  # 缓存
    "\u53ef\u6e05\u7406",  # 可清理
    "\u5019\u9009",  # 候选
    "\u5927\u6587\u4ef6",  # 大文件
    "cleanup",
    "old log",
    "large file",
)
NETWORK_TERMS = (
    "\u7f51\u7edc",  # 网络
    "\u7f51\u7edc\u72b6\u6001",  # 网络状态
    "\u8fde\u901a",  # 连通
    "\u7f51\u5361",  # 网卡
    "\u8def\u7531",  # 路由
    "\u7f51\u5173",  # 网关
    "\u7aef\u53e3",  # 端口
    "\u76d1\u542c",  # 监听
    "network",
    "dns",
    "resolver",
    "route",
    "gateway",
    "socket",
)
SERVICE_TERMS = ("\u670d\u52a1", "service", "systemd", "nginx", "ssh", "sshd")
MEMORY_TERMS = ("\u5185\u5b58", "\u8d1f\u8f7d", "memory", "swap", "oom")
FILESYSTEM_TERMS = ("\u6302\u8f7d", "\u6587\u4ef6\u7cfb\u7edf", "inode", "mount", "filesystem")
PACKAGE_TERMS = ("\u8f6f\u4ef6\u5305", "\u4f9d\u8d56", "\u5b89\u88c5\u5305", "rpm", "package")
SCHEDULE_TERMS = ("\u8ba1\u5212\u4efb\u52a1", "\u5b9a\u65f6\u4efb\u52a1", "crontab", "cron", "timer")
LOGIN_TERMS = ("\u767b\u5f55", "\u767b\u9646", "\u7528\u6237\u6d3b\u52a8", "login", "last")
KERNEL_TERMS = ("\u5185\u6838", "kernel", "dmesg", "oops", "panic")
PROCESS_TERMS = ("\u8fdb\u7a0b", "\u50f5\u5c38", "process", "cpu", "zombie")


class Planner:
    def __init__(
        self,
        llm: LLMProvider,
        mcp: KylinGuardMCPClient,
        server_mode: Literal["DEMO", "READ_ONLY", "CONTROLLED_EXECUTION"] = "READ_ONLY",
    ) -> None:
        self.llm = llm
        self.mcp = mcp
        self.server_mode = server_mode

    def plan(self, goal: str) -> ActionPlan:
        decision = PolicyEngine().classify_input(goal)
        if not decision.allowed:
            return self._forbidden(goal)

        allowed_tools = [
            {
                "name": tool.name,
                "description": tool.description_zh,
                "risk_level": tool.risk_level.value,
                "read_only": tool.read_only,
            }
            for tool in self.mcp.list_tools()
        ]
        required_tools = self.required_tools(goal)
        prompt = (
            f"\u7528\u6237\u76ee\u6807\uff1a{goal}\n"
            f"\u670d\u52a1\u7aef\u8fd0\u884c\u6a21\u5f0f\uff1a{self.server_mode}\n"
            f"\u5141\u8bb8\u5de5\u5177\u53ca\u5176\u56fa\u6709\u98ce\u9669\uff1a{allowed_tools}\n"
            f"\u786e\u5b9a\u6027\u8def\u7531\u8981\u6c42\u8ba1\u5212\u5fc5\u987b\u5305\u542b\u6838\u5fc3\u8bc1\u636e\u5de5\u5177\uff1a{required_tools}\n"
            "ActionPlan.user_goal must copy the user goal exactly.\n"
            "Plan risk must not be lower than selected tool inherent risk.\n"
            "READ_ONLY cleanup requests may only analyze and propose candidates.\n"
            "Disk diagnosis must use disk_usage_scan(path='/').\n"
            "Cleanup candidates must use large_file_scan(path='__cleanup_roots__', min_bytes=10000000, limit=50).\n"
            "Network status must use network_config_snapshot and network_socket_list.\n"
            "\u6240\u6709\u9762\u5411\u7528\u6237\u7684\u6458\u8981\u548c\u7406\u7531\u5fc5\u987b\u4f7f\u7528\u4e2d\u6587\uff1b"
            "\u98ce\u9669\u7b49\u7ea7\u53ea\u80fd\u662f L0/L1/L2/L3/L4\u3002"
        )
        try:
            plan = self.llm.generate_structured(prompt=prompt, schema=ActionPlan)
            self._validate_plan(plan, goal)
            return plan
        except (LLMUnavailableError, ValueError):
            plan = self._rule_fallback(goal)
        self._validate_plan(plan, goal)
        return plan

    def _validate_plan(self, plan: ActionPlan, original_goal: str) -> None:
        if plan.user_goal.strip() != original_goal.strip():
            raise ValueError("GOAL_MISMATCH")
        self._normalize_plan_arguments(plan, original_goal)
        tools = {tool.name: tool for tool in self.mcp.list_tools()}
        risk_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
        for step in plan.steps:
            metadata = tools.get(step.tool_name)
            if metadata is None:
                raise ValueError("TOOL_NOT_REGISTERED")
            if risk_order[plan.risk_level] < risk_order[metadata.risk_level.value]:
                raise ValueError("RISK_DOWNGRADE_REJECTED")
            decision = PolicyEngine().authorize_tool(
                user_goal=plan.user_goal,
                tool_name=step.tool_name,
                read_only=metadata.read_only,
                server_mode=self.server_mode,
            )
            if not decision.allowed:
                raise ValueError(decision.reason_code)
        required_tools = set(self.required_tools(original_goal))
        planned_tools = {step.tool_name for step in plan.steps}
        if not required_tools.issubset(planned_tools):
            raise ValueError("REQUIRED_EVIDENCE_TOOL_MISSING")

    @staticmethod
    def route(goal: str) -> tuple[Intent, Complexity, str]:
        lower = goal.lower()
        disk_goal = Planner._is_disk_goal(lower)
        cleanup_goal = Planner._is_cleanup_goal(lower)
        network_goal = Planner._is_network_goal(lower)

        if disk_goal and cleanup_goal:
            return Intent.CLEANUP, Complexity.COMPLEX, "disk_usage_scan"
        if cleanup_goal:
            return Intent.CLEANUP, Complexity.COMPLEX, "large_file_scan"
        if Planner._contains_any(lower, SERVICE_TERMS):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "service_status"
        if disk_goal:
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "disk_usage_scan"
        if Planner._contains_any(lower, MEMORY_TERMS):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "memory_snapshot"
        if Planner._contains_any(lower, FILESYSTEM_TERMS):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "filesystem_inventory"
        if network_goal and re.search(r"\b\d{1,5}\b", lower):
            return Intent.QUERY, Complexity.SIMPLE, "port_owner_lookup"
        if network_goal:
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "network_config_snapshot"
        if Planner._contains_any(lower, PACKAGE_TERMS):
            return Intent.QUERY, Complexity.MEDIUM, "package_inventory"
        if Planner._contains_any(lower, SCHEDULE_TERMS):
            return Intent.INSPECTION, Complexity.MEDIUM, "scheduled_task_inventory"
        if Planner._contains_any(lower, LOGIN_TERMS):
            return Intent.INSPECTION, Complexity.MEDIUM, "login_audit"
        if Planner._contains_any(lower, KERNEL_TERMS):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "kernel_log_query"
        if Planner._contains_any(lower, PROCESS_TERMS):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "process_list"
        return Intent.QUERY, Complexity.SIMPLE, "system_snapshot"

    @staticmethod
    def required_tools(goal: str) -> tuple[str, ...]:
        lower = goal.lower()
        required: list[str] = []
        if Planner._is_disk_goal(lower):
            required.append("disk_usage_scan")
        if Planner._is_cleanup_goal(lower):
            required.append("large_file_scan")
        if required:
            return tuple(dict.fromkeys(required))
        if Planner._is_network_goal(lower) and not re.search(r"\b\d{1,5}\b", lower):
            return ("network_config_snapshot", "network_socket_list")
        _, _, tool = Planner.route(goal)
        return (tool,)

    @staticmethod
    def _contains_any(lower_goal: str, terms: tuple[str, ...]) -> bool:
        return any(term in lower_goal for term in terms)

    @staticmethod
    def _is_disk_goal(lower_goal: str) -> bool:
        return Planner._contains_any(lower_goal, DISK_TERMS)

    @staticmethod
    def _is_cleanup_goal(lower_goal: str) -> bool:
        return Planner._contains_any(lower_goal, CLEANUP_TERMS)

    @staticmethod
    def _is_network_goal(lower_goal: str) -> bool:
        return Planner._contains_any(lower_goal, NETWORK_TERMS)

    @staticmethod
    def _normalize_plan_arguments(plan: ActionPlan, goal: str) -> None:
        lower = goal.lower()
        for step in plan.steps:
            if step.tool_name == "disk_usage_scan" and Planner._is_disk_goal(lower):
                step.arguments = {"path": "/"}
            if step.tool_name == "large_file_scan" and Planner._is_cleanup_goal(lower):
                step.arguments = {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}
            if step.tool_name == "port_owner_lookup":
                step.arguments = Planner._default_arguments(goal, "port_owner_lookup")

    def _rule_fallback(self, goal: str) -> ActionPlan:
        intent, complexity, primary_tool = self.route(goal)
        required_tools = self.required_tools(goal)
        steps = [
            PlanStep(
                sequence=sequence,
                tool_name=tool,
                arguments=self._default_arguments(goal, tool),
                purpose="\u91c7\u96c6\u53ea\u8bfb\u7cfb\u7edf\u8bc1\u636e",
            )
            for sequence, tool in enumerate(required_tools, start=1)
        ]
        if primary_tool == "service_status":
            service = self._service_name_from_goal(goal)
            steps.append(
                PlanStep(
                    sequence=len(steps) + 1,
                    tool_name="journal_query",
                    arguments={"unit": service, "lines": 50},
                    purpose="\u91c7\u96c6\u670d\u52a1\u6700\u8fd1\u65e5\u5fd7\u4f5c\u4e3a\u8f85\u52a9\u8bc1\u636e",
                )
            )
        risk_level: Literal["L0", "L1", "L2", "L3", "L4"] = (
            "L2" if intent == Intent.CLEANUP or any(self._is_l2_tool(step.tool_name) for step in steps) else "L1"
        )
        return ActionPlan(
            plan_id=str(uuid.uuid4()),
            user_goal=goal,
            intent=intent,
            complexity=complexity,
            summary="\u89c4\u5219\u964d\u7ea7\u751f\u6210\u7684\u53ea\u8bfb\u8bca\u65ad\u8ba1\u5212",
            steps=steps,
            expected_evidence=list(required_tools),
            risk_level=risk_level,
            requires_approval=False,
            verification="\u6821\u9a8c\u5de5\u5177\u8fd4\u56de\u7ed3\u6784\u548c\u8bc1\u636e\u6765\u6e90",
            rollback="\u53ea\u8bfb\u8ba1\u5212\u4e0d\u9002\u7528\u56de\u6eda",
            public_reason=(
                "LLM \u5f53\u524d\u4e0d\u53ef\u7528\u6216\u6a21\u578b\u8ba1\u5212\u4e0d\u7b26\u5408\u89c4\u5219\uff0c"
                "\u5df2\u4f7f\u7528\u786e\u5b9a\u6027\u53ea\u8bfb\u8def\u7531\u91c7\u96c6\u7cfb\u7edf\u8bc1\u636e\u3002"
            ),
        )

    @staticmethod
    def _is_l2_tool(tool_name: str) -> bool:
        return tool_name in {
            "journal_query",
            "network_socket_list",
            "port_owner_lookup",
            "large_file_scan",
            "filesystem_inventory",
            "network_config_snapshot",
            "package_inventory",
            "scheduled_task_inventory",
            "login_audit",
            "kernel_log_query",
            "io_diagnose",
            "security_baseline_scan",
        }

    @staticmethod
    def _default_arguments(goal: str, tool: str) -> dict[str, object]:
        lower = goal.lower()
        if tool == "service_status":
            return {"service": Planner._service_name_from_goal(goal)}
        if tool == "journal_query":
            return {"unit": Planner._service_name_from_goal(goal), "lines": 50}
        if tool == "port_owner_lookup":
            match = re.search(r"\b(\d{1,5})\b", lower)
            port = int(match.group(1)) if match else 80
            return {"port": max(1, min(65535, port))}
        if tool == "large_file_scan":
            return {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}
        if tool == "disk_usage_scan":
            return {"path": "/"}
        if tool in {"package_inventory", "login_audit"}:
            return {"limit": 50}
        if tool == "kernel_log_query":
            return {"lines": 80}
        return {}

    @staticmethod
    def _service_name_from_goal(goal: str) -> str:
        lower = goal.lower()
        if re.search(r"(^|[^a-z0-9_])(ssh|sshd)([^a-z0-9_]|$)", lower):
            return "sshd"
        if "nginx" in lower:
            return "nginx"
        return "nginx"

    @staticmethod
    def _forbidden(goal: str) -> ActionPlan:
        return ActionPlan(
            plan_id=str(uuid.uuid4()),
            user_goal=goal,
            intent=Intent.FORBIDDEN,
            complexity=Complexity.SIMPLE,
            summary="\u8bf7\u6c42\u5df2\u88ab\u5b89\u5168\u89c4\u5219\u62d2\u7edd",
            steps=[],
            expected_evidence=[],
            risk_level="L4",
            requires_approval=False,
            verification="\u672a\u8c03\u7528\u7cfb\u7edf\u5de5\u5177",
            rollback="\u4e0d\u9002\u7528",
            public_reason="\u8bf7\u6c42\u547d\u4e2d\u7981\u6b62\u89c4\u5219\uff0c\u7cfb\u7edf\u672a\u8c03\u7528\u4efb\u4f55\u5de5\u5177\u3002",
        )
