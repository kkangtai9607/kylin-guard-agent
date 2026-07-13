# PLANS.md

> 2026-07-13 最终闭环更新：麒麟 V11 x86_64 VM 已完成真实 `CONTROLLED_EXECUTION` 双人审批端到端冒烟，`service_restart nginx` 经 dry-run、L3 审批、一次性 token、Unix Socket broker、固定 root helper、执行后验证与 token 重放拒绝验证通过；验收后目标机已恢复 `READ_ONLY`，执行代理停用，sudoers/drop-in/临时用户清理完成，审计链复验有效。Phase 10（最终参赛文档、PPT、视频）仍为 `NOT_STARTED`；LoongArch 真机仍未验证。
> 2026-07-12 增量计划：在保持默认 `READ_ONLY` 的前提下，已完成固定动作最小权限执行代理的本地实现与回归。目标机待完成代理组件部署、sudoers 语法核验、Socket/服务隔离核验和单一白名单服务重启演练；未通过前不得设置 `CONTROLLED_EXECUTION`。真实生产的清理、配置更新、进程终止仍保持未开放，待各自的固定 helper 与独立目标机演练完成后再纳入范围。

> 2026-07-12 当前权威状态：Phase 0–8 已完成；Phase 9 的 Windows、麒麟 V11 x86_64 虚拟机部署与真实只读验证已完成，LoongArch 尚未验证，因此保持 `TARGET_VALIDATION_PENDING`。Phase 10（最终参赛文档、PPT、视频）按用户要求保持 `NOT_STARTED`。

本阶段新增能力已完成：垃圾候选分类与快照、五类受控写工具、双人审批令牌领取、结构化证据/RCA/决策链、间接注入隔离、中文前端受控操作台。真实麒麟 VM 仍保持 `READ_ONLY`，未安装 sudoers，未启用生产写操作。

> 2026-07-11 真实性修正：Phase 9 当前权威状态为 `TARGET_VALIDATION_PENDING`。Windows AMD64 本地实现与检查已通过；麒麟 V11 x86_64 VM、systemd、sudoers、Linux MCP 命令路径和部署运行尚待验证，不能再标记为完全完成。Phase 10 仍为 `NOT_STARTED`。

# KylinGuard Agent 阶段计划

## 使用规则

- 当前只允许一个 Phase 标记为 `IN_PROGRESS`
- 完成阶段后更新实际结果
- 未经用户明确指令，不进入下一阶段
- 计划变化必须记录原因

## Phase 状态

| Phase | 名称 | 状态 | 主要产物 |
|---|---|---|---|
| 0 | 规划与架构 | COMPLETED | 架构、威胁模型、ER、API、评分映射 |
| 1 | 工程骨架与后端基础 | COMPLETED | FastAPI、DB、Auth、状态机、审计基础 |
| 2 | MCP 与只读感知 | COMPLETED | MCP Server/Client、感知 Tools |
| 3 | 安全护栏与审批 | COMPLETED | Policy、RBAC、Approval、RestrictedExecutor 框架 |
| 4 | Agent 编排与 LLM | COMPLETED | LLMProvider、Planner、ReAct、降级 |
| 5 | RCA 与知识库 | COMPLETED | 多源证据、Top3 根因、FTS5 |
| 6 | 受控执行与回滚 | COMPLETED | 清理、重启、配置修改、终止进程、回滚 |
| 7 | 前端产品化 | COMPLETED | 驾驶舱、对话、审批、插件、审计 |
| 8 | 增强功能 | COMPLETED | 趋势预警、配置漂移、哈希链 |
| 9 | 测试与部署 | COMPLETED | 麒麟部署、LoongArch 检查、性能和安全测试 |
| 10 | 比赛交付 | NOT_STARTED | 九项材料、PPT、7 分钟演示、发布冻结 |

## 当前阶段

- Current Phase: Phase 9
- Status: COMPLETED
- Approved scope: 用户已授权连续执行 Phase 2 至 Phase 9；逐阶段验收后自动推进，不制作比赛文档、PPT 或视频。
- Stop condition: Phase 2 至 Phase 9 全部实现并完成当前环境可执行的真实验收，未验证的麒麟/LoongArch 项明确记录。
- Verification commands:
  - `python scripts/validate_phase0.py`
  - `python scripts/security_scan.py`
  - 使用指定 uv 与 Python 3.10 复跑上述两个脚本
  - 凭据模式与危险设计关键词只读扫描
  - `uv run alembic upgrade head`
  - `uv run pytest`
  - `uv run ruff check backend mcp_server scripts`
  - `uv run mypy backend mcp_server`
  - `npm run type-check` 与 `npm run build`

## 阶段变更记录

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-07-11 | Phase 0 从 NOT_STARTED 更新为 COMPLETED | 架构、安全、接口、ER、配置、评分映射、演示脚本和验证材料完成并通过检查 |
| 2026-07-11 | Phase 1 从 NOT_STARTED 更新为 COMPLETED | 后端基础闭环、迁移、测试、静态检查和最小前端构建通过 |
| 2026-07-11 | Phase 2 至 Phase 9 获得连续执行授权，Phase 2 标记 IN_PROGRESS | 用户要求目标模式连续构建并最终统一验收 |
| 2026-07-11 | Phase 2 完成，Phase 3 自动进入 IN_PROGRESS | 官方 MCP SDK 1.28.1 smoke test、14 个只读 Tool、DEMO/READ_ONLY Provider 与安全测试通过 |
| 2026-07-11 | Phase 3 完成，Phase 4 自动进入 IN_PROGRESS | 确定性策略、审批持久化/RBAC、HMAC 令牌、dry-run Executor 与 27 项测试通过 |
| 2026-07-11 | Phase 4 完成，Phase 5 自动进入 IN_PROGRESS | Provider、结构化规划、白名单复核、规则降级、Agent API/SSE 与 33 项回归通过 |
| 2026-07-11 | Phase 5 完成，Phase 6 自动进入 IN_PROGRESS | 可解释 RCA、证据追踪、FTS5、知识审核/API 与 38 项测试通过 |
| 2026-07-11 | Phase 6 完成，Phase 7 自动进入 IN_PROGRESS | DEMO 沙箱 5 个受控 Tool、审批绑定、备份/验证/回滚与故障注入测试通过 |
| 2026-07-11 | Phase 7 完成，Phase 8 自动进入 IN_PROGRESS | 12 个真实 API 路由页面、任务闭环、权限/错误反馈、类型检查与生产构建通过 |
| 2026-07-11 | Phase 8 完成，Phase 9 自动进入 IN_PROGRESS | EWMA/Z-score、配置漂移脱敏、审计哈希链/篡改检测与 API 完成 |
| 2026-07-11 | Phase 9 完成，停止在 Phase 10 之前 | 当前主机全量验收、部署静态审计、性能数据和 Phase 2–9 完成矩阵通过；麒麟/LoongArch 真机项明确保留 |

