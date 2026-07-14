# CURRENT_STATUS.md

## 2026-07-14 LoongArch cryptography 构建兼容修复

- 官方麒麟 LoongArch VM 第三轮安装失败定位为 `cryptography==49.0.0` 源码构建链引入 `archery 1.2.2`，该 Rust crate 同样要求 Cargo `edition2024`，目标机 Cargo 1.82.0 无法解析，导致 `metadata-generation-failed`。
- 已进一步收紧部署依赖：显式锁定 `cryptography==42.0.8` 与 `cffi==1.17.1`，避免解析到 2026 年新 Rust 依赖链；继续保持 `mcp==1.28.1` 与 `pydantic-core==2.33.2`。
- 本轮真实回归：`uv run pytest -q` 110 项通过（仅 Starlette TestClient 第三方弃用警告）；`uv run ruff check backend mcp_server scripts` 通过；`uv run mypy backend mcp_server` 通过（88 个源文件）；`uv run python scripts/security_scan.py` 通过（196 个文本/源码文件）；`uv run python scripts/validate_phase0.py` 通过。
- LoongArch 仍需在官方 VM 使用最新 `main` 重新拉取后验证；若后续仍有源码构建失败，优先继续收紧依赖或改用离线 wheelhouse，不升级系统 Rust 作为首选路径。

## 2026-07-14 LoongArch 安装依赖兼容修复

- 官方麒麟 LoongArch VM 第二轮安装失败定位为依赖构建问题：pip 拉取到过新的 `pydantic-core` 源码包，构建元数据时要求 Rust/Cargo `edition2024`，而目标机 Cargo 1.82.0 不支持该特性，导致 `metadata-generation-failed`。
- 已调整 Python 依赖约束并重新导出 `deploy/requirements.txt`：保持官方 MCP SDK `mcp==1.28.1`，锁定 `pydantic==2.11.10`、`pydantic-core==2.33.2`、`pydantic-settings==2.10.1`，并将项目 Python 范围限定为 `>=3.10,<3.14`，避免解析到需要更新 Rust edition 的后续依赖组合。
- 本轮修复不写入任何 Secret，不改变默认 `READ_ONLY` 模式，不开启生产写执行；仍要求目标机安装 `python3-devel gcc make libffi-devel openssl-devel rust cargo`，首轮 `Python.h` 缺失问题需由系统开发头文件解决。
- 本地真实回归：`uv run pytest -q` 110 项通过（仅 Starlette TestClient 第三方弃用警告）；`uv run ruff check backend mcp_server scripts` 通过；`uv run mypy backend mcp_server` 通过（88 个源文件）；`uv run python scripts/security_scan.py` 通过（196 个文本/源码文件）；`uv run python scripts/validate_phase0.py` 通过。
- LoongArch 真机安装结果仍待用户在官方 VM 上使用最新源码重试后确认；不得将当前 Windows 本地回归冒充为 LoongArch 已验证。

## 2026-07-13 受控执行最终闭环验收（以本节为准）

- 新增 `scripts/target_controlled_execution_smoke.py`，用于目标机真实 API 双人审批受控执行冒烟；脚本只从环境变量读取临时账号密码，使用 HTTP JSON 序列化提交审批 token，不打印、不落盘任何密码或 token。
- 麒麟 V11 x86_64 VM 已完成真实链路验收：临时切换 `CONTROLLED_EXECUTION`，创建独立操作员 `final-op` 与审批员 `final-ap`，完成 `service_restart nginx` dry-run、L3 审批、审批员批准、请求方 claim 一次性 token、Unix Socket broker 固定 helper 重启 nginx、执行后验证、token 重放拒绝与审计校验。结果：`execution_status=SUCCEEDED`，`verification="service=nginx; active=true; state_snapshot=active"`，重放请求 HTTP `403`，`audit_valid=true`，执行耗时约 `312.162ms`。
- 验收后已恢复 VM 默认安全基线：`kylin-guard` active，`kylin-guard-exec` inactive，`/etc/sudoers.d/kylin-guard` absent，临时 controlled-execution drop-in absent，健康接口 `meta.mode=READ_ONLY`，临时用户数量 `0`，审计链复验 `AUDIT_VALID=True`。
- 本地安全修正：`.env.example` 已恢复为空 Secret 占位；真实 DeepSeek Key 与 VM 密码不再保存在仓库文件中，仅允许使用 Windows 用户环境变量或目标机 root-only secret 文件注入。
- 本轮真实回归：`pytest -q` 110 项通过（仅 Starlette TestClient 第三方弃用警告）；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过（88 个源文件）；`security_scan.py` 通过（196 个文本/源码文件）；`validate_phase0.py` 通过；`release_audit.py` 通过；前端 `npm run type-check` 与 `npm run build` 通过。Vite 仍提示 Element Plus chunk 大于 500KB，属于性能优化项，不影响功能验收。
- 当前边界：最终参赛文档、PPT、视频仍未启动；LoongArch 真机仍未验证，当前只能声明 Kylin V11 x86_64 VM 验证通过，不能冒充 LoongArch 结果。

## 2026-07-13 麒麟受控执行目标机复验进度（以本节为准）

- 已在麒麟 V11 x86_64 VM 验证：固定 Unix Socket 代理、peer UID 拒绝、严格 sudoers、root 固定 helper、POSIX ACL 审批库最小访问、一次性审批状态原子消费和 `nginx` 固定重启均可工作；验证后已删除临时审批记录、临时账户、sudoers 和受控模式 drop-in，VM 恢复 `READ_ONLY`，执行代理保持停用。
- API 双人审批路径的旧诊断脚本存在 Python 运算符优先级错误，曾将 `error=None` 错误显示为失败；需要以正确的 `data.status == SUCCEEDED` 断言复验后才可正式标记通过。LoongArch 仍未验证。

## 2026-07-12 受控执行代理增量（以本节为准）

- 新增固定动作的最小权限执行链：`kylin-guard` API（无 sudo、`NoNewPrivileges=true`）通过本地 Unix Socket 调用 `kylin-guard-exec`，后者只可经 sudo 启动 root 所有的固定 helper；helper 仅接受 `service_restart nginx`，最终只执行固定绝对路径的 `systemctl restart nginx`。
- 默认仍为 `READ_ONLY`：安装脚本只安装代理组件，不安装 sudoers、不启动代理、不切换模式。代理缺失时，生产重启 dry-run/执行均安全拒绝；不存在直接 sudo、root API 或任意命令降级路径。
- 新增代理协议单元测试；2026-07-12 本地全量回归已实际通过：`pytest -q`、`ruff check backend mcp_server scripts`、`mypy backend mcp_server`（88 个源文件）、`security_scan.py`（194 个文本/源码文件）、`validate_phase0.py` 和 `release_audit.py`。TestClient 有一个第三方弃用警告，不影响结果。
- 麒麟 V11 x86_64 上尚未部署本次代理增量；当前 VM 继续仅验证 `READ_ONLY`。LoongArch 仍未验证。最终参赛文档、PPT、视频仍未启动。

## 2026-07-12 最新权威状态

- 目标模式持续执行：除最终参赛文档、PPT、视频外，功能与验证持续补齐。
- 本地 Windows：后端 96 项测试、Ruff、mypy、安全扫描通过；前端 type-check/build 通过。
- 麒麟 V11 x86_64 VM `192.168.140.169`：真实部署运行成功，麒麟 V11 Swan25、内核 6.6.0-32.7.v2505、Python 3.11.6；systemd、journalctl、lsof、ss、iostat、sudo、nginx 均可用。
- VM 服务：`kylin-guard` active，API 仅监听 `127.0.0.1:8000`，非 root `kylin-guard` 账号，默认 `READ_ONLY`；数据库迁移已到 `0009_agent_trace`。
- VM 真实只读回归：14 个 MCP Tool 中核心能力调用成功；服务状态曾暴露自检参数缺失问题，已修复并重新同步。在线诊断状态 `SUCCEEDED`，标准化证据 6 条，RCA 候选 2 个，审计链 `valid=true`。
- VM 性能实测：40 次并发健康请求 mean 54.325ms、p95 76.363ms；系统概览 mean 6.169ms；只读诊断约 7197.463ms；结果见 `data/performance-kylin-v11-x86_64.json`。
- 安全边界：VM 未安装 sudoers，未启用 `CONTROLLED_EXECUTION`；真实生产写执行保持关闭。DEMO 写闭环与本地受控执行器测试通过，但不冒充 VM 生产写验证。
- LoongArch：尚未验证；当前只能标记 `DESIGNED`，不能替代真机测试。

> 2026-07-12 DEMO 前端闭环：新增 `/demo`“安全演示闭环”页面，展示操作员发起、dry-run、独立审批员登录、一次性令牌、备份、执行、验证、自动回滚和审计校验；审批员密码提交后立即从组件内存清空，审批 Token 不展示、不落盘，禁止自审批仍由后端强制。登录状态现从响应 meta 持久化真实模式，READ_ONLY 页面明确禁用 DEMO 操作。Vite 代理支持 `VITE_API_PROXY_TARGET`，正常入口保持 5173→8000，隔离演示入口为 5174→8001。前端类型检查、生产构建和安全扫描通过；最新静态资源已同步 VM，但 VM 模式保持 READ_ONLY。当前隔离 DEMO 服务为 8001/5174，正常本地服务为 8000/5173。

> 2026-07-12 隔离 DEMO 受控执行验收：新增 `scripts/demo_execution_smoke.py`，使用独立 8001 端口、独立 SQLite 数据库、独立 operator/approver 和 `demo/runtime` 沙箱完成真实 API 闭环。`safe_log_cleanup` dry-run 后强制审批，生成备份并验证释放 3100 字节，执行 19.255ms；审批令牌重放返回 403。`config_safe_update` 故障注入后状态 ROLLED_BACK、从备份恢复、rollback_status=SUCCEEDED，37.138ms。`service_restart`、`terminate_process`、配置安全更新和显式 `rollback_change` 均成功，耗时分别 17.555/28.853/34.988/25.165ms；审计链有效。临时 DEMO 服务已关闭，8001 不再监听；本地 8000/5173 与 VM `READ_ONLY` 均健康。全量 59 项测试、ruff、mypy、安全扫描通过。所有写动作仅作用于隔离演示资源，麒麟真实写执行和 sudoers 仍关闭。

> 2026-07-12 三轮演示稳定性与离线降级：新增 `scripts/demo_stability_smoke.py`。麒麟 VM 连续三轮 DeepSeek 磁盘诊断均成功，耗时 5058.787/4969.120/4676.934ms，平均 4901.614ms；每轮均为 L2、包含 `disk_usage_scan` 与 `large_file_scan`、生成 2 条证据。注入场景保持 BLOCKED/0 证据，巡检 201，审计链有效，三轮总耗时远低于 7 分钟。独立进程移除 LLM 环境变量后，确定性 `disk_usage_scan` 降级成功，在线服务和 Secret 未修改。稳定性测试首次发现模型计划语义拒绝后 API 返回 500，现改为拒绝模型候选并再次校验确定性只读降级计划；测试仍直接验证幻觉工具、目标不一致、风险下调和核心证据遗漏会被拒绝。测试环境新增自动清除真实 LLM 凭据，防止回归测试意外调用在线 API。最终 59 项测试、ruff、mypy、安全扫描通过；本地后端已重启加载修复。

> 2026-07-12 麒麟 VM 性能与安全稳定性验收：新增 `scripts/target_performance_smoke.py`，凭据仅从环境变量读取。VM `READ_ONLY` 实测 40 次/8 并发健康请求 mean 178.609ms、P95 247.707ms；10 次系统概览 mean 25.073ms、P95 31.195ms；真实巡检 74.754ms；DeepSeek 在线完整诊断 6320.767ms、状态 SUCCEEDED、证据 2 条；审计链校验 21.543ms 且 valid=true。服务 `NRestarts=0`，近期无 warning 日志，内存约 75–95MB，数据库 224KB；后端仅监听 127.0.0.1:8000，Nginx 对外监听 80。VM API 直接注入“读取 /etc/shadow”被判定 L4/BLOCKED，Tool 步骤和证据均为 0。结果保存于 `data/performance-kylin-v11-x86_64.json`，仅代表麒麟 V11 x86_64，不代表 LoongArch。

> 2026-07-12 重启恢复与 VM 同步：Windows 本地后端、前端已重新启动，健康检查均为 HTTP 200；后端从 Windows 用户环境变量读取 DeepSeek 配置。SSH 使用既有 ed25519 指纹重新连接 `192.168.140.169`，VM 上 `kylin-guard` 与 Nginx 均为 active，模式保持 `READ_ONLY`。已将最新 DeepSeek Provider、L0–L4 严格风险、目标一致性、风险下限和核心证据工具校验同步到麒麟 VM；Secret 仅写入 `/etc/kylin-guard/secrets.env`（0640，root:kylin-guard），未显示 Key。VM 上 DeepSeek JSON 冒烟和磁盘 `ActionPlan` 均在线通过，计划为 L2、工具为 `disk_usage_scan` 与 `large_file_scan`；sudoers 仍未安装，生产写执行仍关闭。

> 2026-07-11 DeepSeek 本地在线联调完成：官方 `deepseek-v4-pro` 最小 JSON Schema 调用通过；复杂 `ActionPlan` 初测暴露非标准风险标签、目标改写、风险下调、核心证据遗漏和默认思考模式超时，均未进入工具执行。现已将风险收紧为 L0–L4 枚举，强制目标逐字一致、模型风险不得低于工具固有风险、确定性意图路由核心工具不得遗漏，并把工具中文说明和风险元数据提供给模型。结构化规划显式设置 `thinking: disabled`，不请求或保存隐藏思维；最终在线磁盘诊断约 12 秒返回 L2 计划，选择 `disk_usage_scan` 与 `large_file_scan`，中文摘要和理由通过。完整回归 59 项、ruff、mypy、安全扫描通过。新 Key 仅从 Windows 用户环境变量读取，未写入仓库。

> 2026-07-11 按钮与 DeepSeek 联调准备：新增独立高对比按钮主题，修复 `.panel span` 覆盖 Element Plus 按钮文字颜色的问题；普通、主操作、成功、危险、文字与禁用按钮均定义明确背景和文字色，并已同步到麒麟 VM。前端类型检查和生产构建通过。DeepSeek Provider 已按官方 JSON Output 要求补充实际 JSON Schema 与 `max_tokens`，新增 `scripts/deepseek_smoke.py`；本机未配置新的 `DEEPSEEK_API_KEY`，在线调用尚未执行，脚本按预期安全退出。聊天中曾暴露的旧 Key 不得复用。

> 2026-07-11 麒麟 VM 验证：已在 `Kylin Linux Advanced Server V11 (Swan25)` x86_64、内核 `6.6.0-32.7.v2505.ky11.x86_64` 上完成首次 `READ_ONLY` 部署。Python 3.11.6、SQLite 3.42.0/FTS5/WAL、systemd 255、清华 PyPI 源、Nginx 1.24 已验证；数据库迁移为 `0005_audit_head`。systemd 使用 `kylin-guard` 非 root 账号、`NoNewPrivileges=yes`、`ProtectSystem=strict`，只允许写 `/opt/kylin-guard/data`，sudoers 未安装。14 个只读 MCP 工具全部真实执行成功；Windows 经 Nginx 访问前端和 API 为 HTTP 200，登录、系统概览、真实只读巡检分别为 200/200/201。部署过程中修复代码目录组权限、麒麟 Nginx 默认站点冲突和生产审计脚本漂移。该结果标记为 `KYLIN_X86_64_VERIFIED`，不能替代 `LOONGARCH_VERIFIED`；生产写适配器仍关闭，Phase 10 未启动。

> 2026-07-11 前端可读性加固：参考 `claude-code-system-prompts` 的状态色、表面层级、信息优先和可访问性原则，完成界面中文化与高对比度重构。侧边栏、登录、驾驶舱、运维对话、审批、任务时间线、MCP 工具及管理页面已清理乱码；只读模式、运行正常、任务与审批状态使用中文映射；内容区与表格改为白色高对比表面，数字和正文改为深灰蓝；运维任务主按钮改为青绿色。前端类型检查与生产构建通过。

> 2026-07-11 最新状态（优先于下方历史记录）：Phase 9 为 `TARGET_VALIDATION_PENDING`，不是完全完成。已完成迁移前本地加固：定时巡检接入 FastAPI lifespan（默认关闭、受信任配置显式开启）、巡检异常自动生成事件、事件状态闭环、六个管理页面真实操作、首次只读安装不启用 sudoers、安装包补齐 `alembic.ini`。55 项 pytest、ruff、mypy、安全扫描、前端类型检查与生产构建通过。Windows API 实测七个管理端点均返回 HTTP 200。麒麟 V11 x86_64 VM 尚待安装验证，LoongArch 仍未验证；Phase 10 未启动，未制作参赛文档、PPT 或视频。

# 当前项目状态

## 1. 当前阶段

- Phase: Phase 9（测试、部署与兼容审计）
- 状态: COMPLETED
- 最后更新时间: 2026-07-11

## 2. 已完成功能

- Phase 0 需求、总体架构和业务闭环设计
- 威胁模型、风险等级、独立确定性护栏与信任边界设计
- Agent 状态机与受控执行生命周期设计
- MCP Tool 元数据规范、数据库 ER 和 API 草案
- 三种运行模式、配置样例、比赛评分映射和 7 分钟演示脚本
- Phase 0 文档一致性和安全扫描脚本
- FastAPI 应用、统一响应、错误处理和健康检查
- 严格配置加载，默认 `READ_ONLY`
- SQLite WAL、SQLAlchemy 基础模型和 Alembic 初始迁移
- scrypt 密码哈希、会话令牌摘要、用户/角色/RBAC、管理员创建和登录
- Agent Task、Task Step 与显式状态机
- 审计事件基础写入、递归脱敏和受保护查询
- pytest、ruff、mypy、uv 锁文件和最小 Vue/Vite 工程骨架
- 官方 MCP Python SDK 1.28.1 集成与 FastMCP 14 Tool 注册 smoke test
- 后端 MCP Client、Tool Registry、严格元数据与统一 `UNTRUSTED_DATA` 输出
- DEMO 和真实 READ_ONLY Provider，以及 14 个只读感知 Tool/安全降级骨架
- Phase 3 确定性输入/Tool/路径策略、审批持久化、独立审批 RBAC、HMAC 一次性令牌
- Phase 4 OpenAI-compatible/DeepSeek Provider、Mock/降级、结构化计划、Agent API 与 SSE
- Phase 5 Evidence、可解释 Top 3 RCA、冲突降权、SQLite FTS5 与知识审核 API
- Phase 6 DEMO 沙箱 5 个受控 Tool、候选 ID、备份、验证、故障注入与回滚
- Phase 7 登录、驾驶舱、任务、审批、MCP、巡检、RCA、漂移、知识、审计和设置路由页面
- Phase 8 EWMA/Z-score、配置差异脱敏、审计 SHA-256 哈希链与篡改检测
- Phase 9 安装/卸载/健康检查、systemd、Nginx、sudoers、平台探测、依赖导出和真实性能脚本

## 3. 当前可运行入口

- Backend: `uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Frontend: `cd frontend; npm run dev`（仅最小骨架）
- MCP Server: `uv run python -m mcp_server.server`（stdio，14 个只读 Tool）
- Demo: 后续阶段实现，当前无模拟业务数据

Phase 2–9 已完成当前主机可验证的实现和验收。真实生产写操作在目标麒麟环境验证前保持关闭；Phase 10 未启动。

## 4. 最近测试结果

| 命令 | 结果 | 日期 |
|---|---|---|
| `python scripts/security_scan.py`（首次） | 失败：空 Secret 占位符被跨行正则误报；已修复扫描器 | 2026-07-11 |
| `python scripts/security_scan.py`（修复后） | 通过：检查 38 个文本/源码文件 | 2026-07-11 |
| `python scripts/validate_phase0.py` | 通过：检查 22 个必需文件、链接、关键术语、状态与配置样例 | 2026-07-11 |
| 指定 uv + Python 3.10 + 清华源运行 `validate_phase0.py` | 通过：22 个必需文件 | 2026-07-11 |
| 指定 uv + Python 3.10 + 清华源运行 `security_scan.py` | 通过：38 个文本/源码文件 | 2026-07-11 |
| 凭据模式 `rg` 扫描 | 通过：未发现已落盘的非空 API Key/Bearer 凭据 | 2026-07-11 |
| `pytest` / `ruff` / `mypy` | 不适用：Phase 1 尚未创建 Python 工程 | 2026-07-11 |
| `npm run type-check` / `npm run build` | 不适用：Phase 7 尚未创建前端工程 | 2026-07-11 |
| Git 状态/diff | 不可用：当前目录不是 Git 仓库，Phase 0 未擅自初始化 | 2026-07-11 |
| 指定 uv 清华源 `sync --python 3.10` | 通过：Python 3.10.17，依赖已锁定 | 2026-07-11 |
| `uv run alembic upgrade head` | 通过：创建 10 个表，SQLite `journal_mode=wal` | 2026-07-11 |
| 管理员 CLI + 登录 + `/auth/me` | 通过：HTTP 200/200 | 2026-07-11 |
| `uv run pytest` | 通过：9 passed；1 个第三方 TestClient 弃用警告 | 2026-07-11 |
| `uv run ruff check backend mcp_server scripts` | 通过 | 2026-07-11 |
| `uv run mypy backend mcp_server` | 通过：34 个源码文件 | 2026-07-11 |
| `uv run python scripts/security_scan.py` | 通过：82 个文本/源码文件 | 2026-07-11 |
| `npm audit` | 通过：0 vulnerabilities | 2026-07-11 |
| `npm run type-check` / `npm run build` | 通过：Vite 生产构建成功 | 2026-07-11 |
| FastMCP SDK smoke test | 通过：官方 SDK 1.28.1 实际注册并列出 14 个 Tool | 2026-07-11 |
| Phase 2 `uv run pytest` | 通过：16 passed | 2026-07-11 |
| Phase 2 ruff / mypy / security_scan | 通过：41 个源码文件类型检查，93 个文件安全扫描 | 2026-07-11 |
| Phase 3 全套回归 | 通过：27 passed；46 个源码文件 mypy；99 文件安全扫描 | 2026-07-11 |
| Phase 4 全套回归 | 通过：33 passed；Provider/Agent/SSE 测试通过 | 2026-07-11 |
| Phase 5 全套回归 | 通过：38 passed；RCA/FTS5/API 测试通过 | 2026-07-11 |
| Phase 6 受控执行专项 | 通过：5 Tool DEMO 沙箱、故障回滚、重放/篡改测试 | 2026-07-11 |
| Phase 7 前端 | 通过：npm audit 0、类型检查、Vite 生产构建 | 2026-07-11 |
| Phase 8 增强专项 | 通过：趋势、漂移脱敏、哈希链篡改检测 | 2026-07-11 |
| Phase 9 当前全套回归 | 通过：45 passed、ruff、59 源码 mypy、136 文件安全扫描、npm audit 0、前端构建 | 2026-07-11 |
| Phase 9 Alembic 空库升级 | 通过：0001→0002→0003 | 2026-07-11 |
| 当前主机性能 smoke | health mean 10.224ms/p95 10.971ms；DEMO snapshot mean 0.007ms；非麒麟/LoongArch | 2026-07-11 |
| Phase 2–9 最终 pytest | 通过：53 passed；1 个第三方 TestClient 弃用警告 | 2026-07-11 |
| Phase 2–9 最终 ruff / mypy / security | 通过：64 个源码文件 mypy，146 个文本/源码文件安全扫描 | 2026-07-11 |
| Phase 2–9 completion audit | 通过：实际 API 路由、FastMCP 14 Tool、核心实现符号、前端与部署产物 | 2026-07-11 |
| 最终前端检查 | npm audit 0；type-check/build 通过；ECharts 按需构建 | 2026-07-11 |

## 5. 当前安全状态

- `shell=True` 扫描: 安全扫描未发现源码违规
- 任意 Shell Tool: 设计明确禁止，未创建此类 Tool
- 写操作审批: L3 设计为强制人工审批，L4 永久拒绝
- 路径保护: 已定义 allowed roots、protected paths、规范化、符号链接与执行前复核
- 敏感信息脱敏: 已定义字段白名单、Secret 外置和统一脱敏；示例 Secret 均为空
- 审计完整性: canonical JSON SHA-256 哈希链、数据库链头串行化、校验/导出和篡改定位已实现

## 6. 已知问题

- 当前 Windows 环境无法验证麒麟高级服务器 V11、systemd、sudoers 和 `/proc`/`/sys` 行为。
- 无 LoongArch64 真机，依赖、MCP SDK、SQLite FTS5/WAL 和性能只能标记为 `DESIGNED`。
- 用户曾通过非保密聊天渠道提供 API Key，该 Key 不在仓库中；必须在 Provider 端撤销并轮换后才能供后续阶段使用。
- 当前不是 Git 仓库，无法进行基于提交历史和 diff 的审查。
- FastAPI/Starlette TestClient 报第三方弃用警告，不影响当前测试；后续依赖升级时跟踪。
- Phase 1 的测试数据库是本地验证产物，已被 `.gitignore` 排除。
- 当前 Windows 无 Bash，部署脚本只完成静态审计，未运行 `bash -n` 或目标机安装。
- LoongArch 上 MCP/cryptography/cffi/greenlet 的构建与 wheel 可用性待真机验证。
- 前端 Element Plus vendor chunk gzip 约 281KB，生产可用但仍可继续按需加载优化。

## 7. 下一阶段候选工作

- Phase 10 仅在用户明确指令后开始；比赛文档、PPT、视频当前不制作。
- 迁移到参赛环境后执行麒麟 V11/LoongArch 真机安装、依赖构建、命令路径、sudoers、systemd sandbox 和性能复验。

## 8. 重要决策

- LLM 没有最终执行权限，确定性规则引擎拥有最终否决权。
- 禁止任意 Shell；Executor 只接受 Guardrail 签发的结构化内部授权。
- 默认模式为 `READ_ONLY`；所有 L3 写操作强制人工审批、备份、验证和失败回滚。
- 不保存或展示模型隐藏思维，只保留结构化决策链和公开理由摘要。
- DeepSeek 为默认可配置 Provider，同时预留其他模型适配接口；Secret 仅从环境或系统 Secret 注入。
- Docker、GPU、向量数据库、本地大模型和 x86 专属二进制均不是硬依赖。

