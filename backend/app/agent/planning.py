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
            f"用户目标：{goal}\n"
            f"服务端运行模式：{self.server_mode}\n"
            f"允许工具及其固有风险：{allowed_tools}\n"
            f"确定性路由要求计划必须包含核心证据工具：{required_tools}\n"
            "ActionPlan.user_goal 必须逐字复制用户目标，不得改写、翻译或概括。\n"
            "计划风险不得低于所选工具的最高固有风险。\n"
            "READ_ONLY 模式中的清理请求只能分析并生成候选，不得选择写工具或声称已经清理。\n"
            "磁盘占用诊断必须使用 disk_usage_scan(path='/')。\n"
            "可清理候选必须使用 large_file_scan(path='__cleanup_roots__', min_bytes=10000000, limit=50)。\n"
            "所有面向用户的摘要和理由必须使用中文；风险等级只能是 L0、L1、L2、L3、L4。"
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
        if disk_goal and cleanup_goal:
            return Intent.CLEANUP, Complexity.COMPLEX, "disk_usage_scan"
        if cleanup_goal:
            return Intent.CLEANUP, Complexity.COMPLEX, "large_file_scan"
        if any(term in lower for term in ("nginx", "ssh", "sshd", "服务", "service", "systemd", "鏈嶅姟")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "service_status"
        if disk_goal:
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "disk_usage_scan"
        if any(term in lower for term in ("内存", "memory", "swap", "oom", "鍐呭瓨")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "memory_snapshot"
        if any(term in lower for term in ("挂载", "文件系统", "inode", "mount", "filesystem", "鎸傝浇", "鏂囦欢绯荤粺")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "filesystem_inventory"
        if any(term in lower for term in ("端口", "port", "socket", "绔彛")) and re.search(r"\b\d{1,5}\b", lower):
            return Intent.QUERY, Complexity.SIMPLE, "port_owner_lookup"
        if any(term in lower for term in ("端口", "port", "socket", "绔彛")):
            return Intent.QUERY, Complexity.SIMPLE, "network_socket_list"
        if any(term in lower for term in ("路由", "网卡", "dns", "resolver", "route", "ip地址", "网络配置", "璺敱", "缃戝崱")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "network_config_snapshot"
        if any(term in lower for term in ("软件包", "rpm", "依赖", "安装包", "package", "杞欢鍖?")):
            return Intent.QUERY, Complexity.MEDIUM, "package_inventory"
        if any(term in lower for term in ("计划任务", "定时任务", "crontab", "cron", "timer", "璁″垝浠诲姟")):
            return Intent.INSPECTION, Complexity.MEDIUM, "scheduled_task_inventory"
        if any(term in lower for term in ("登录", "登陆", "login", "last", "用户活动", "鐧诲綍")):
            return Intent.INSPECTION, Complexity.MEDIUM, "login_audit"
        if any(term in lower for term in ("内核", "kernel", "dmesg", "oops", "panic", "鍐呮牳")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "kernel_log_query"
        if any(term in lower for term in ("进程", "process", "cpu", "僵尸", "杩涚▼", "鍍靛案")):
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
        _, _, tool = Planner.route(goal)
        return (tool,)

    @staticmethod
    def _is_disk_goal(lower_goal: str) -> bool:
        return any(
            term in lower_goal
            for term in (
                "磁盘",
                "硬盘",
                "空间",
                "容量",
                "disk",
                "filesystem usage",
                "纾佺洏",
                "绌洪棿",
            )
        )

    @staticmethod
    def _is_cleanup_goal(lower_goal: str) -> bool:
        return any(
            term in lower_goal
            for term in (
                "清理",
                "垃圾",
                "旧日志",
                "缓存",
                "可清理",
                "候选",
                "cleanup",
                "old log",
                "娓呯悊",
                "鍨冨溇",
                "缂撳瓨",
            )
        )

    @staticmethod
    def _normalize_plan_arguments(plan: ActionPlan, goal: str) -> None:
        lower = goal.lower()
        for step in plan.steps:
            if step.tool_name == "disk_usage_scan" and Planner._is_disk_goal(lower):
                step.arguments = {"path": "/"}
            if step.tool_name == "large_file_scan" and Planner._is_cleanup_goal(lower):
                step.arguments = {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}

    def _rule_fallback(self, goal: str) -> ActionPlan:
        intent, complexity, primary_tool = self.route(goal)
        required_tools = self.required_tools(goal)
        steps = [
            PlanStep(
                sequence=sequence,
                tool_name=tool,
                arguments=self._default_arguments(goal, tool),
                purpose="采集只读系统证据",
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
                    purpose="采集服务最近日志作为辅助证据",
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
            summary="规则降级生成的只读诊断计划",
            steps=steps,
            expected_evidence=list(required_tools),
            risk_level=risk_level,
            requires_approval=False,
            verification="校验工具返回结构和证据来源",
            rollback="只读计划不适用回滚",
            public_reason="LLM 当前不可用或模型计划不符合规则，已使用确定性只读路由采集系统证据。",
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
            summary="请求已被安全规则拒绝",
            steps=[],
            expected_evidence=[],
            risk_level="L4",
            requires_approval=False,
            verification="未调用系统工具",
            rollback="不适用",
            public_reason="请求命中禁止规则，系统未调用任何工具。",
        )
