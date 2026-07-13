# 数据库 ER 设计

## 1. 关系概览

```text
users ──< user_roles >── roles
users ──< sessions
users ──< agent_tasks ──< task_steps
                         ├──< evidence
                         ├──< guard_decisions
                         ├──< tool_calls >── mcp_tools
                         ├──< approvals ──0..1 executions
                         │                    ├──< backups
                         │                    ├──< verification_results
                         │                    └──< rollback_records
                         └──< audit_events

system_snapshots ──< incidents >── evidence
knowledge_documents ──< knowledge_cases
config_baselines
settings
```

## 2. 核心实体

| 表 | 关键字段 | 约束 |
|---|---|---|
| users | id、username、status、version | username 唯一；不保存明文密码 |
| roles | id、name | name 唯一 |
| user_roles | user_id、role_id | 复合唯一 |
| sessions | id、user_id、expires_at、revoked_at | 会话令牌只存安全摘要 |
| agent_tasks | id、user_id、goal、mode、intent、risk、state、version | mode 不得由任务提升 |
| task_steps | id、task_id、sequence、state、public_reason | sequence 唯一 |
| evidence | id、task_id、source_type、source_ref、summary、content_hash、trust_label | 默认不存敏感原文 |
| tool_calls | id、task_id、tool_id、normalized_args_hash、status、duration_ms | 参数按白名单脱敏 |
| guard_decisions | id、task_id、stage、decision、risk、reason_code | 保存规则结果，不存隐藏思维 |
| approvals | id、task_id、approver_id、tool_name、params_hash、nonce_hash、expires_at、status、consumed_at | nonce 单次消费；L4 不创建 |
| executions | id、task_id、approval_id、status、started_at、finished_at | approval_id 可空仅限无写执行 |
| backups | id、execution_id、target_ref、backup_ref、content_hash、status | Secret 不进入 backup_ref |
| verification_results | id、execution_id、strategy、status、summary | 结构化验证结果 |
| rollback_records | id、execution_id、status、verification_status、summary | 记录回滚后验证 |
| audit_events | id、task_id、actor_id、event_type、payload_summary、previous_hash、current_hash、created_at | 只追加 |
| mcp_tools | id、name、version、metadata_json、enabled | name+version 唯一 |
| system_snapshots | id、host_ref、captured_at、summary_hash、is_demo | DEMO 明确标识 |
| incidents | id、snapshot_id、severity、status、summary | 可关联多证据 |
| knowledge_documents | id、source、review_status、max_risk_support、content_hash | 未审核不得支持 L3 |
| knowledge_cases | id、document_id、resolution_status、reviewer_id | 只有已审核案例进入执行建议 |
| config_baselines | id、path_ref、content_hash、version_label、approval_id | 不保存敏感配置原文 |
| settings | key、value_json、version | 只保存非秘密设置或 Secret 引用名 |

## 3. 通用约束

- 主键使用 UUID，时间使用 UTC，状态使用受控枚举。
- 可变业务实体包含乐观版本字段；状态更新在事务中比较版本。
- SQLite 启用外键、WAL 和受控 busy timeout；写事务保持短小。
- 索引覆盖任务状态/时间、审批状态/过期时间、审计任务/时间和知识检索字段。
- 迁移由 Alembic 管理；禁止应用启动时隐式破坏性迁移。
- FTS5 索引仅保存允许检索的脱敏内容。

## 4. 审计哈希

事件使用稳定字段顺序的 canonical JSON：

```text
current_hash = SHA256(canonical_json(event_without_hash) + previous_hash)
```

链可按分区/日期设置锚点，但锚点规则必须在 Phase 8 前通过 ADR 固化。

