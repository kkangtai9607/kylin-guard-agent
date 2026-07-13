# Agent 状态机

## 1. 状态

```text
RECEIVED
→ INPUT_GUARD
→ INTENT_CLASSIFIED
→ CONTEXT_COLLECTING
→ PLANNED
→ PLAN_GUARD
→ TOOL_CALLING
→ EVIDENCE_READY
→ ROOT_CAUSE_ANALYZED
→ ACTION_PROPOSED
→ ACTION_GUARD
→ DRY_RUN
→ WAITING_APPROVAL
→ APPROVED
→ BACKING_UP
→ EXECUTING
→ VERIFYING
→ SUCCEEDED
```

辅助状态：`ROLLING_BACK`。终态：`SUCCEEDED`、`FAILED`、`BLOCKED`、`ROLLED_BACK`、`CANCELLED`。

## 2. 关键迁移规则

| 当前状态 | 条件 | 下一状态 |
|---|---|---|
| INPUT_GUARD | L4/注入/越权命中 | BLOCKED |
| PLAN_GUARD | Schema、Tool、模式或范围不合法 | BLOCKED |
| EVIDENCE_READY | 纯查询且无需 RCA | SUCCEEDED |
| ROOT_CAUSE_ANALYZED | 仅诊断 | SUCCEEDED |
| ACTION_GUARD | READ_ONLY 中出现写操作 | BLOCKED |
| ACTION_GUARD | L4 | BLOCKED |
| DRY_RUN | 预检失败 | FAILED |
| WAITING_APPROVAL | 拒绝、超时或参数变化 | CANCELLED/BLOCKED |
| APPROVED | 令牌有效且原子消费成功 | BACKING_UP |
| BACKING_UP | 备份失败 | FAILED |
| VERIFYING | 验证成功 | SUCCEEDED |
| VERIFYING | 验证失败且可回滚 | ROLLING_BACK |
| ROLLING_BACK | 回滚后验证成功 | ROLLED_BACK |
| ROLLING_BACK | 回滚失败 | FAILED |

## 3. 模式规则

- DEMO：只允许隔离演示根目录内的状态变更，仍经过 guard、审批、备份、验证和审计。
- READ_ONLY：在 `ACTION_GUARD` 阻止全部写操作。
- CONTROLLED_EXECUTION：仅注册 L3 Tool 在有效审批后进入 `BACKING_UP`。

## 4. 取消与并发

取消只在安全检查点生效。已经开始的写操作不能跳过验证或回滚。状态迁移使用服务端枚举表、乐观版本字段和事务更新，拒绝非法或重复迁移；不得用零散布尔变量表示流程。

## 5. 审计字段

每次迁移记录任务、前后状态、公开原因码、操作者、时间、证据引用和事件哈希。不保存模型隐藏思维、原始 Secret 或未经脱敏的 Tool 输出。

