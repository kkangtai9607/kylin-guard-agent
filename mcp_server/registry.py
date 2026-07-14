from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp_server.providers import DemoProvider, ReadOnlyProvider
from mcp_server.schemas.models import RiskLevel, ToolMetadata, ToolResult

ToolCallable = Callable[..., dict[str, Any]]


TOOL_DESCRIPTIONS = {
    "capability_probe": ("能力探测", "探测操作系统、架构和受控命令能力", RiskLevel.L1),
    "system_snapshot": ("系统快照", "采集基础系统资源快照", RiskLevel.L1),
    "process_list": ("进程列表", "读取受限数量的进程信息", RiskLevel.L1),
    "zombie_process_scan": ("僵尸进程扫描", "扫描 Z 状态进程", RiskLevel.L2),
    "network_socket_list": ("监听端口", "读取网络监听信息", RiskLevel.L2),
    "port_owner_lookup": ("端口归属", "查询指定端口归属", RiskLevel.L2),
    "disk_usage_scan": ("磁盘用量", "读取允许目录的磁盘用量", RiskLevel.L1),
    "large_file_scan": ("大文件扫描", "在允许目录内扫描大文件", RiskLevel.L2),
    "open_file_lookup": ("文件占用", "查询文件是否正在被进程使用", RiskLevel.L2),
    "journal_query": ("日志查询", "读取受限的 systemd journal 日志", RiskLevel.L2),
    "service_status": ("服务状态", "查询白名单服务状态", RiskLevel.L1),
    "config_drift_check": ("配置漂移", "只读比较配置基线", RiskLevel.L2),
    "io_diagnose": ("I/O 诊断", "读取 I/O 统计数据", RiskLevel.L2),
    "security_baseline_scan": ("安全基线", "运行只读安全基线检查", RiskLevel.L2),
}


class ToolRegistry:
    def __init__(self, provider: ReadOnlyProvider, is_demo: bool = False) -> None:
        self.provider = provider
        self.is_demo = is_demo
        self._metadata = {
            name: ToolMetadata(
                name=name,
                title_zh=title,
                description_zh=description,
                risk_level=risk,
                timeout_seconds=20,
                max_output_bytes=131072,
            )
            for name, (title, description, risk) in TOOL_DESCRIPTIONS.items()
        }

    @classmethod
    def for_mode(
        cls,
        mode: str,
        allowed_roots: tuple[Path, ...] | None = None,
        cleanup_roots: tuple[Path, ...] | None = None,
    ) -> ToolRegistry:
        return (
            cls(DemoProvider(), is_demo=True)
            if mode == "DEMO"
            else cls(ReadOnlyProvider(allowed_roots=allowed_roots, cleanup_roots=cleanup_roots))
        )

    def list_tools(self) -> list[ToolMetadata]:
        return list(self._metadata.values())

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        if name not in self._metadata:
            return ToolResult(
                tool_name=name,
                status="FAILED",
                data={},
                error_code="TOOL_NOT_REGISTERED",
                is_demo=self.is_demo,
            )
        method = getattr(self.provider, name)
        try:
            data = method(**(arguments or {}))
            truncated = bool(data.pop("truncated", False))
            return ToolResult(
                tool_name=name,
                status="SUCCEEDED",
                data=data,
                truncated=truncated,
                is_demo=self.is_demo,
            )
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            return ToolResult(
                tool_name=name,
                status="FAILED",
                data={},
                warnings=[str(error)[:500]],
                error_code=type(error).__name__.upper(),
                is_demo=self.is_demo,
            )
