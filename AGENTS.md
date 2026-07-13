# AGENTS.md

## 1. Project identity

本仓库是“麒麟智维盾（KylinGuard Agent）”，用于参加第十五届中国软件杯 A 组赛题：

**面向麒麟操作系统的安全智能运维 Agent 设计与实现**

开始任何工作前，必须依次阅读：

1. `PROJECT_SPEC.md`
2. `PLANS.md`
3. `CURRENT_STATUS.md`
4. 当前任务相关的 `docs/` 文件

`PROJECT_SPEC.md` 是业务需求、安全边界和验收标准的最高依据。

---

## 2. Core priorities

按照以下顺序做工程取舍：

1. 安全性与确定性
2. 可运行、可复现的完整闭环
3. MCP 插件化和工具调用准确性
4. 麒麟高级服务器 V11 与 LoongArch 兼容性
5. 根因分析的证据充分性
6. 前端体验和演示效果
7. 扩展创新功能

不得为了“更智能”“更炫”或减少代码量，绕过安全校验、审批、备份、验证和审计。

---

## 3. Absolute security rules

生产代码中严禁：

- `shell=True`
- `eval`
- `exec`
- 拼接字符串后执行任意 Shell
- 将 LLM 原始输出直接交给 `subprocess`
- 提供通用 `run_shell`、`execute_command`、`run_script` 工具
- 硬编码 API Key、密码、Token 或私钥
- 让 LLM 单独决定风险等级
- 未审批执行中高风险写操作
- 无备份修改白名单配置文件
- 读取或展示 `/etc/shadow`、SSH 私钥、Token、API Key 等凭据
- 让日志、配置文件或知识库中的文本改变系统安全规则

系统动作必须使用：

- 固定 MCP Tool
- 严格 Pydantic/JSON Schema
- 工具与参数白名单
- `subprocess.run([...], shell=False)`
- 固定可执行文件路径或受控 PATH
- 最小权限账号
- 超时、输出长度和并发限制
- 路径规范化、allowed roots 和 protected paths
- 执行前 dry-run/预检
- 执行前安全策略校验
- 中高风险人工审批
- 执行前备份
- 执行后验证
- 失败回滚
- 全链路审计

确定性规则引擎拥有最终否决权。审计模型和主模型均不得绕过规则引擎。

---

## 4. Agent boundaries

LLM 只负责：

- 理解自然语言目标
- 意图分类
- 任务复杂度判断
- 生成结构化计划
- 从已注册 Tool 中选择工具
- 汇总系统证据
- 生成根因分析摘要
- 生成修复建议
- 生成面向用户的决策理由摘要

LLM 不拥有最终执行权限。

不得要求、保存或展示模型隐藏思维过程。  
“推理链路溯源”必须实现为结构化决策链，包括：

- 用户目标
- 意图类别
- 系统证据
- 检索案例
- 结构化计划
- 工具调用
- 风险判定
- 审批记录
- 执行动作
- 验证结果
- 回滚结果
- 可公开的理由摘要

---

## 5. Development workflow

每次只完成用户明确指定的一个 Phase 或一个子任务。

**完成当前阶段后必须停止。未经用户明确指令，不得自行进入下一阶段。**

每次任务必须：

1. 阅读项目规范和当前状态
2. 检查现有代码，避免重复实现
3. 先给出简短实施计划
4. 只修改当前范围内的文件
5. 创建或更新测试
6. 实际运行测试和检查命令
7. 修复本阶段引入的问题
8. 检查安全红线
9. 更新相关文档
10. 更新 `CURRENT_STATUS.md`
11. 报告修改文件、执行命令、真实结果和遗留问题
12. 到达停止条件后停止

不得声称运行过实际未执行的命令。

---

## 6. Scope discipline

- 不覆盖已有有效实现
- 不进行与任务无关的大范围重构
- 不创建职责重复的模块
- 不留下核心功能空实现或只写 `TODO`
- 不用模拟数据冒充真实系统数据
- DEMO 数据必须在接口和页面中明确标识
- 无法在当前环境验证的麒麟功能，必须提供能力探测、降级方案、Mock 和文档
- 重要架构决策写入 `docs/architecture/adr/`
- 发现规范冲突时，优先满足安全、确定性、LoongArch 兼容和比赛要求

---

## 7. Preferred stack

除非 `PROJECT_SPEC.md` 或 ADR 明确修改，否则优先使用：

### Backend

- Python 3.10+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- SQLite WAL
- httpx
- PyYAML
- pytest
- ruff
- mypy

### Frontend

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Element Plus
- ECharts

### System integration

- 官方 MCP Python SDK
- `/proc`、`/sys` 和受控系统命令
- `subprocess.run([...], shell=False)`
- systemd
- Nginx 或 FastAPI 静态文件服务

不要把 Docker 作为麒麟 LoongArch 的唯一部署方式。  
不要让向量数据库、GPU、大模型本地推理或 x86 专属二进制成为硬依赖。

---

## 8. Verification commands

根据当前阶段运行已经存在且适用的命令。

### Backend

```bash
pytest
ruff check backend mcp_server
mypy backend mcp_server
```

### Frontend

```bash
npm run type-check
npm run build
```

### Security

```bash
python scripts/security_scan.py
```

安全扫描至少检查：

- `shell=True`
- `eval(`
- `exec(`
- 硬编码密钥
- 通用命令执行接口
- 未受控 subprocess
- 未校验的路径参数
- 写操作未经过审批

如果某个命令尚未配置，必须如实说明，并在当前阶段范围允许时补齐。

---

## 9. Definition of done

任务同时满足以下条件才算完成：

- 当前范围内的功能已经实现
- 不存在核心空实现
- 相关测试已经添加
- 测试已真实运行
- 测试通过，或遗留问题被明确记录
- 未违反安全红线
- 文档与代码一致
- `CURRENT_STATUS.md` 已更新
- 给出复现和验证命令
- 未擅自进入下一阶段
