# 麒麟智维盾（KylinGuard Agent）

面向麒麟高级服务器操作系统的安全智能运维 Agent。系统以自然语言理解和结构化规划为入口，以确定性安全规则、固定 MCP Tool、人工审批、最小权限执行和全链路审计为执行边界。

## 当前状态

- 当前完成阶段：Phase 9（功能、前端、测试与部署准备）
- 可运行入口：FastAPI API、独立 MCP Server、Vue 生产前端与 DEMO 安全执行闭环
- 下一阶段：Phase 10 比赛交付，按用户要求保持未启动，不制作比赛文档、PPT 或视频

## 核心安全原则

- LLM 没有最终执行权限；其输出只能作为通过严格 Schema 校验的候选计划。
- 确定性规则引擎拥有最终否决权，任何模型均不得绕过。
- 禁止任意 Shell、命令字符串执行和通用命令执行 Tool。
- L3 写操作强制人工审批，并依次完成 dry-run、备份、执行、验证和失败回滚。
- L4 凭据访问、破坏性、越权和逃逸请求始终拒绝。
- 日志、配置、网络响应、知识库和历史案例均按 `UNTRUSTED_DATA` 隔离。
- 不请求、保存或展示模型隐藏思维，只记录结构化决策链和公开理由摘要。

## 运行模式

| 模式 | 数据与权限 |
|---|---|
| `DEMO` | 固定可复现数据，仅允许修改隔离演示资源，页面和接口强制标记演示数据 |
| `READ_ONLY` | 读取真实系统状态，禁止所有状态变更；默认模式 |
| `CONTROLLED_EXECUTION` | 仅允许白名单受控写操作，L3 强制审批、备份、验证和回滚 |

## 架构文档

- [软件功能需求分析](docs/01-软件功能需求分析.md)
- [软件功能设计](docs/02-软件功能设计.md)
- [接口文档](docs/07-接口文档.md)
- [安全设计说明](docs/08-安全设计说明.md)
- [比赛评分点映射](docs/09-比赛评分点映射.md)
- [7 分钟演示脚本](docs/10-演示脚本.md)
- [总体架构](docs/architecture/总体架构.md)
- [业务闭环](docs/architecture/业务闭环.md)
- [Agent 状态机](docs/architecture/Agent状态机.md)
- [威胁模型](docs/architecture/威胁模型.md)
- [MCP Tool 元数据规范](docs/architecture/MCP-Tool元数据规范.md)
- [数据库 ER 设计](docs/architecture/数据库ER设计.md)
- [初始技术选型 ADR](docs/architecture/adr/0001-初始技术选型.md)

## 配置与凭据

配置样例位于 `config/`。`.env.example` 仅包含空 Secret 占位符。任何 API Key、Token、密码或私钥不得进入仓库、数据库、日志、前端或审计事件。已经通过聊天或其他非保密渠道暴露的 Key 必须撤销并重新生成。

后续本地 Python 环境使用指定 `uv.exe` 启动器创建 Python 3.10+ 环境，并通过清华 PyPI 源安装依赖。该 uv 文件所在的 Python 3.8 路径不改变项目最低 Python 版本。

## Phase 1 本地运行

```powershell
$env:UV_DEFAULT_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" sync --python 3.10
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run alembic upgrade head
$env:KYLIN_GUARD_BOOTSTRAP_PASSWORD = Read-Host "Initial admin password"
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run python -m backend.app.cli create-admin --username admin
Remove-Item Env:KYLIN_GUARD_BOOTSTRAP_PASSWORD
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/health`。停止服务请在运行窗口按 `Ctrl+C`。

前端开发入口：

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1
```

默认模式是 `READ_ONLY`。如需验证隔离 DEMO 审批—执行—回滚闭环，只能在无真实资源的开发环境中临时设置 `KYLIN_GUARD_MODE=DEMO` 和新生成的 `APPROVAL_HMAC_KEY`；生产写适配器在麒麟真机验收前保持关闭。

质量检查：

```powershell
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run pytest
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run ruff check backend mcp_server scripts
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run mypy backend mcp_server
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run python scripts/security_scan.py
& "C:\Users\tang\AppData\Local\Programs\Python\Python38\Scripts\uv.exe" run python -m scripts.completion_audit
```
