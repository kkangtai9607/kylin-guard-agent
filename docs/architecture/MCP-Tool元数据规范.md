# MCP Tool 元数据规范

## 1. 元数据 Schema

每个 Tool 必须登记：

```yaml
name: service_status
version: 1.0.0
title_zh: 查询服务状态
description_zh: 查询白名单 systemd 服务的只读状态
input_schema: {}
output_schema: {}
risk_level: L1
read_only: true
allowed_modes: [DEMO, READ_ONLY, CONTROLLED_EXECUTION]
allowed_roles: [operator, approver, admin]
timeout_seconds: 10
max_output_bytes: 65536
max_concurrency: 4
preconditions: []
executable_policy: fixed_argv
allowed_executables: [/usr/bin/systemctl]
path_policy: null
supports_dry_run: false
idempotency: read_only
requires_approval: false
backup_strategy: none
verification_strategy: schema_and_exit_code
rollback_strategy: none
sensitive_fields: []
audit_fields: [service_name, exit_code, duration_ms]
error_codes: []
platform_capabilities: [systemd]
```

## 2. 注册约束

- `name + version` 唯一；版本变更遵循语义化版本。
- 输入和输出使用严格 JSON Schema；拒绝额外字段并限制字符串、枚举、数值和数组长度。
- Tool 不得接收命令字符串、脚本内容、解释器参数或任意可执行路径。
- `risk_level` 是不可被 LLM 降低的下限。
- 写 Tool 必须是 L3，声明 dry-run、人工审批、备份、验证、回滚和幂等策略。
- L4 能力不得注册为 Tool。
- 启动时校验元数据完整性、模式组合和可执行路径；无效注册使该 Tool 禁用。

## 3. 标准输出信封

```json
{
  "tool_call_id": "uuid",
  "status": "SUCCEEDED",
  "data": {},
  "evidence_ids": ["uuid"],
  "warnings": [],
  "truncated": false,
  "duration_ms": 25,
  "error": null
}
```

Tool 输出进入 LLM 前必须补充来源、类型、采集时间、内容哈希并标记 `UNTRUSTED_DATA`。敏感字段在持久化和显示前脱敏。

## 4. 标准错误码

`SCHEMA_INVALID`、`MODE_FORBIDDEN`、`RBAC_DENIED`、`CAPABILITY_UNAVAILABLE`、`PATH_REJECTED`、`PROTECTED_RESOURCE`、`APPROVAL_REQUIRED`、`APPROVAL_EXPIRED`、`APPROVAL_REPLAYED`、`TIMEOUT`、`OUTPUT_TRUNCATED`、`BACKUP_FAILED`、`EXECUTION_FAILED`、`VERIFICATION_FAILED`、`ROLLBACK_FAILED`。

## 5. 首批 Tool 范围

只读：`capability_probe`、`system_snapshot`、`process_list`、`zombie_process_scan`、`network_socket_list`、`port_owner_lookup`、`disk_usage_scan`、`large_file_scan`、`open_file_lookup`、`journal_query`、`service_status`、`config_drift_check`、`io_diagnose`、`security_baseline_scan`。

受控写：`safe_log_cleanup`、`service_restart`、`config_safe_update`、`terminate_process`、`rollback_change`。这些 Tool 留到 Phase 6 实现，且必须满足完整 L3 契约。

