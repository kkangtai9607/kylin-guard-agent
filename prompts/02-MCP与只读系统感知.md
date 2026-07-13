# Phase 2：MCP 与只读系统感知

```text
阅读项目规范和当前状态。

本次只执行 Phase 2：MCP Server、MCP Client 和第一批只读系统感知工具。完成后停止。

开始前先检查当前官方 MCP Python SDK 的实际安装版本和 API，用最小 smoke test 验证后再集成。不要凭记忆编写过期接口。

实现：

1. 独立 MCP Server；
2. 后端 MCP Client；
3. Tool Registry；
4. Tool 元数据模型；
5. MCP 连通性健康检查；
6. DEMO 和真实 READ_ONLY 两种 Provider；
7. capability_probe；
8. system_snapshot；
9. process_list；
10. zombie_process_scan；
11. network_socket_list；
12. port_owner_lookup；
13. disk_usage_scan；
14. large_file_scan；
15. open_file_lookup；
16. journal_query；
17. service_status；
18. config_drift_check 的只读骨架；
19. io_diagnose；
20. security_baseline_scan。

实现要求：

- 优先读取 /proc、/sys；
- 系统命令使用固定 executable 和参数数组；
- shell=False；
- 命令能力探测；
- ss 缺失时降级 netstat；
- iostat、lsof 缺失时提供降级或明确错误；
- 输出统一 JSON；
- 控制超时、最大行数和最大字节；
- 路径扫描限制在 allowed roots；
- 不跟随危险符号链接；
- 进程命令行和日志自动脱敏；
- 工具输出标记为 UNTRUSTED_DATA；
- 工具失败不得导致 API 服务崩溃；
- DEMO 数据明确标注。

创建单元和集成测试，包括：

- Tool 注册；
- 参数校验；
- 超时；
- 命令缺失；
- DEMO/真实模式；
- 输出截断；
- 敏感信息脱敏；
- 路径越界；
- 符号链接。

验收：

- 后端可通过 MCP 调用工具；
- MCP Tool 列表可查询；
- system_snapshot 能返回统一数据；
- 所有工具为只读；
- 全项目无通用 Shell Tool；
- 测试和安全扫描通过。

完成后更新文档、CURRENT_STATUS.md 和 PLANS.md，然后停止。
```
