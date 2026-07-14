from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.agent.cleanup import CleanupAnalysisService
from backend.app.agent.normalization import EvidenceNormalizer
from backend.app.agent.planning import ActionPlan, Intent, Planner
from backend.app.agent.rca import RCAEngine
from backend.app.agent.runners import PlanAndExecuteRunner, ReActRunner, ResponseComposer
from backend.app.guardrails.untrusted import sanitize_text
from backend.app.mcp_client.client import KylinGuardMCPClient


class AgentOrchestrator:
    def __init__(
        self,
        planner: Planner,
        mcp: KylinGuardMCPClient,
        knowledge_search: Callable[[str], list[Any]] | None = None,
    ) -> None:
        self.planner = planner
        self.mcp = mcp
        self.knowledge_search = knowledge_search

    def run(self, goal: str) -> dict[str, Any]:
        plan = self.planner.plan(goal)
        if plan.intent == Intent.FORBIDDEN:
            return {
                "plan": plan.model_dump(mode="json"),
                "evidence": [],
                "normalized_evidence": [],
                "root_causes": [],
                "knowledge_hits": [],
                "cleanup_analysis": [],
                "status": "BLOCKED",
                "diagnosis": self._diagnosis(
                    plan=plan,
                    status="BLOCKED",
                    evidence=[],
                    cleanup_analysis=[],
                ),
                "decision_chain": [
                    {"stage": "用户目标", "reason_code": "GOAL_RECEIVED", "summary": goal},
                    {
                        "stage": "输入护栏",
                        "reason_code": "FORBIDDEN_INPUT",
                        "summary": "请求被确定性安全规则阻断，未调用系统工具。",
                    },
                ],
            }
        evidence, status = PlanAndExecuteRunner(ReActRunner(self.mcp)).run(plan)
        composed = ResponseComposer().compose(plan, evidence, status)
        normalized = EvidenceNormalizer().normalize(evidence)
        root_causes = RCAEngine().analyze(normalized)
        knowledge_hits: list[dict[str, Any]] = []
        if self.knowledge_search is not None:
            try:
                hits = self.knowledge_search(goal)
                knowledge_hits = [
                    {
                        "document_id": item.document_id,
                        "title": item.title,
                        "snippet": sanitize_text(item.snippet, max_text_bytes=4096),
                        "review_status": item.review_status,
                        "trust_label": "UNTRUSTED_DATA",
                    }
                    for item in hits[:5]
                    if item.review_status == "APPROVED"
                ]
            except (OSError, ValueError):
                knowledge_hits = []
        cleanup_analysis: list[dict[str, Any]] = []
        if plan.intent == Intent.CLEANUP and evidence:
            decisions = CleanupAnalysisService(self.mcp).analyze_large_file_result(
                evidence[0].payload
            )
            cleanup_analysis = [item.model_dump(mode="json") for item in decisions]
        return {
            "plan": plan.model_dump(mode="json"),
            **composed,
            "normalized_evidence": [item.model_dump(mode="json") for item in normalized],
            "root_causes": [item.model_dump(mode="json") for item in root_causes],
            "knowledge_hits": knowledge_hits,
            "cleanup_analysis": cleanup_analysis,
            "diagnosis": self._diagnosis(
                plan=plan,
                status=status,
                evidence=evidence,
                cleanup_analysis=cleanup_analysis,
            ),
            "decision_chain": self._decision_chain(
                plan=plan,
                status=status,
                evidence_count=len(normalized),
                root_cause_count=len(root_causes),
                knowledge_count=len(knowledge_hits),
            ),
        }

    @staticmethod
    def _decision_chain(
        *,
        plan: ActionPlan,
        status: str,
        evidence_count: int,
        root_cause_count: int,
        knowledge_count: int,
    ) -> list[dict[str, object]]:
        return [
            {"stage": "用户目标", "reason_code": "GOAL_ACCEPTED", "summary": plan.user_goal},
            {
                "stage": "意图分类",
                "reason_code": f"INTENT_{plan.intent.value}",
                "summary": f"复杂度 {plan.complexity.value}",
            },
            {
                "stage": "结构化计划",
                "reason_code": "PLAN_SCHEMA_VALID",
                "summary": f"{len(plan.steps)} 个白名单步骤，风险 {plan.risk_level}",
            },
            {
                "stage": "确定性护栏",
                "reason_code": "POLICY_ALLOWED",
                "summary": "工具、模式、参数和风险下限校验通过",
            },
            {
                "stage": "证据与知识",
                "reason_code": "UNTRUSTED_DATA_ISOLATED",
                "summary": f"{evidence_count} 条证据，{knowledge_count} 条已审核知识命中",
            },
            {
                "stage": "根因分析",
                "reason_code": "RCA_SCORED",
                "summary": f"生成 {root_cause_count} 个可解释候选",
            },
            {"stage": "任务结果", "reason_code": status, "summary": "公开决策摘要"},
        ]

    @staticmethod
    def _diagnosis(
        *,
        plan: ActionPlan,
        status: str,
        evidence: list[Any],
        cleanup_analysis: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if plan.intent == Intent.FORBIDDEN:
            return {
                "level": "critical",
                "headline": "请求已被安全策略阻断",
                "answer": "该请求命中 L4 禁止规则，系统没有调用任何工具，也没有读取敏感文件。",
                "findings": ["未执行系统访问", "未产生工具调用", "无需回滚"],
                "recommendations": ["请改用只读诊断类问题，例如检查磁盘、服务、端口或进程状态。"],
            }

        by_tool = {record.tool_name: record.payload for record in evidence}
        findings: list[str] = []
        recommendations: list[str] = []
        level = "ok" if status == "SUCCEEDED" else "warning"
        headline = "只读诊断完成"
        answer = "已完成只读证据采集，未执行任何写操作。"

        if "service_status" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["service_status"])
            service = str(data.get("service", "nginx"))
            raw_properties = data.get("properties")
            properties: dict[str, Any] = raw_properties if isinstance(raw_properties, dict) else {}
            active = str(properties.get("ActiveState", "unknown"))
            sub = str(properties.get("SubState", "unknown"))
            result = str(properties.get("Result", "unknown"))
            if active == "active":
                headline = f"{service} 当前未发现运行异常"
                answer = f"{service} 当前 ActiveState=active，SubState={sub}，Result={result}。本次只读检查没有发现服务处于 failed/inactive 状态。"
                level = "ok"
            elif active in {"failed", "inactive"}:
                headline = f"{service} 当前状态异常"
                answer = f"{service} 当前 ActiveState={active}，SubState={sub}，Result={result}，需要结合日志继续定位。"
                level = "critical"
            else:
                headline = f"{service} 当前状态未知"
                answer = f"{service} 当前 ActiveState={active}，SubState={sub}，Result={result}。这通常表示 systemd 能力不可用、服务不在白名单输出中，或工具回执缺少状态字段。"
                level = "warning"
            findings.append(f"服务状态：ActiveState={active}，SubState={sub}，Result={result}")
            if "journal_query" in by_tool:
                journal = AgentOrchestrator._tool_data(by_tool["journal_query"])
                raw_lines = journal.get("lines")
                lines: list[Any] = raw_lines if isinstance(raw_lines, list) else []
                findings.append(f"最近 journal 日志：采集 {len(lines)} 行")
            recommendations.append("如需执行重启，必须切换 CONTROLLED_EXECUTION 并经过人工审批；READ_ONLY 下不会重启服务。")

        elif "disk_usage_scan" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["disk_usage_scan"])
            total = AgentOrchestrator._number(data.get("total"))
            used = AgentOrchestrator._number(data.get("used"))
            free = AgentOrchestrator._number(data.get("free"))
            percent = used / total * 100 if total > 0 else 0.0
            path = str(data.get("path", "."))
            level = "critical" if percent >= 95 else "warning" if percent >= 80 else "ok"
            headline = "磁盘空间压力较高" if level != "ok" else "磁盘空间未达到告警阈值"
            answer = f"扫描路径 {path} 的磁盘使用率为 {percent:.1f}%，可用空间 {AgentOrchestrator._format_bytes(free)}。"
            findings.append(
                f"磁盘：已用 {AgentOrchestrator._format_bytes(used)} / 总计 {AgentOrchestrator._format_bytes(total)}，使用率 {percent:.1f}%"
            )
            recommendations.append("如果需要找可清理对象，请输入“分析磁盘空间不足的原因，并列出安全清理候选”。")

        elif "large_file_scan" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["large_file_scan"])
            raw_files = data.get("files")
            files: list[Any] = raw_files if isinstance(raw_files, list) else []
            eligible_count = sum(1 for item in cleanup_analysis if item.get("eligible"))
            headline = "发现安全清理候选" if eligible_count else "未发现可安全清理候选"
            level = "warning" if eligible_count else "ok"
            answer = (
                f"已在允许目录内扫描大文件，发现 {len(files)} 个超过阈值的大文件；"
                f"其中 {eligible_count} 个同时满足路径、保留期、文件类型、大小和占用状态规则。"
            )
            if files:
                top = sorted(
                    [item for item in files if isinstance(item, dict)],
                    key=lambda item: AgentOrchestrator._number(item.get("size")),
                    reverse=True,
                )[:5]
                for item in top:
                    findings.append(
                        f"大文件：{item.get('path')}（{AgentOrchestrator._format_bytes(AgentOrchestrator._number(item.get('size')))})"
                    )
            else:
                findings.append("未发现超过 10 MB 的大文件，或当前允许目录中没有可扫描对象。")
            if not eligible_count:
                findings.append("没有进入候选的常见原因：未达保留期、文件类型不允许、位于保护路径、文件正在使用或不在 allowed roots 内。")
            recommendations.append("READ_ONLY 模式只展示候选，不会删除；真正清理必须走 dry-run、审批、备份、执行、验证流程。")

        elif "process_list" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["process_list"])
            raw_processes = data.get("processes")
            processes: list[Any] = raw_processes if isinstance(raw_processes, list) else []
            headline = "进程与 CPU 线索已采集"
            answer = f"已读取 {len(processes)} 个进程条目，并按累计 CPU ticks 排序展示可疑进程线索；这不是任意 shell 输出。"
            for item in processes[:5]:
                if isinstance(item, dict):
                    findings.append(
                        f"进程 PID={item.get('pid')}，name={item.get('name')}，state={item.get('state')}，cpu_ticks={item.get('cpu_ticks', 0)}"
                    )
            recommendations.append("如需瞬时 CPU 百分比，可后续增加固定 ps/top 采样 Tool；当前版本优先使用 /proc 只读数据。")

        elif "port_owner_lookup" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["port_owner_lookup"])
            raw_matches = data.get("matches")
            matches: list[Any] = raw_matches if isinstance(raw_matches, list) else []
            port = data.get("port")
            headline = f"端口 {port} {'存在监听线索' if matches else '未发现监听'}"
            answer = f"已查询端口 {port}，匹配到 {len(matches)} 条监听记录。"
            findings.extend(str(line) for line in matches[:5])
            if not matches:
                findings.append("未在 ss/netstat 输出中发现该端口。")
            recommendations.append("如发现陌生监听端口，应结合进程列表和服务归属继续确认。")

        elif "system_snapshot" in by_tool:
            data = AgentOrchestrator._tool_data(by_tool["system_snapshot"])
            disk = data.get("disk") if isinstance(data.get("disk"), dict) else {}
            load = data.get("load_average")
            cpu_count = data.get("cpu_count")
            headline = "系统快照已采集"
            answer = f"主机 {data.get('hostname', 'unknown')} 的基础资源快照采集完成。"
            if disk:
                total = AgentOrchestrator._number(disk.get("total"))
                used = AgentOrchestrator._number(disk.get("used"))
                percent = used / total * 100 if total > 0 else 0
                findings.append(f"磁盘使用率 {percent:.1f}%")
            findings.append(f"CPU 核心数 {cpu_count}，负载 {load}")

        if not findings:
            findings.append("本次没有可展示的结构化发现，请查看原始工具回执确认能力是否缺失。")
        if not recommendations:
            recommendations.append("建议结合标准化证据和原始工具回执继续排查。")
        return {
            "level": level,
            "headline": headline,
            "answer": answer,
            "findings": findings[:8],
            "recommendations": recommendations[:5],
        }

    @staticmethod
    def _tool_data(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _number(value: object) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0

    @staticmethod
    def _format_bytes(value: float) -> str:
        units = ("B", "KB", "MB", "GB", "TB")
        size = value
        index = 0
        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1
        return f"{size:.1f} {units[index]}" if index else f"{size:.0f} B"
