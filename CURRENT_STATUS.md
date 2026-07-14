# CURRENT_STATUS.md

## 2026-07-15 清理候选排除明细展示修复

- 针对“结论显示发现 5 个超过阈值的大文件，但清理候选区域仍显示本次没有清理候选”的反馈，已拆分“扫描到的大文件”和“可直接发起清理的候选”：即使某个大文件因为类型、保护路径、占用状态或保留期被排除，也会在表格中展示路径、大小、类型和排除原因，不再只给出 0 个可清理候选的摘要。
- `CleanupDecision` 新增 `observed_file` 字段；`candidate` 仍只代表可发起清理的已冻结候选，前端表格使用 `candidate || observed_file` 展示扫描结果，按钮只在 `eligible=true` 且存在 `candidate_id` 时可点。
- 该修复不放宽删除边界：被排除的大文件仅可查看原因，不能发起删除；真正清理仍必须满足候选规则并经过预检查、风险确认、备份、执行、验证和审计。
- 本轮真实回归：`npm run type-check` 通过；`npm run build` 通过（仅 Vite chunk 体积提示）；`uv run ruff check backend mcp_server` 通过；`uv run mypy backend mcp_server` 通过；`uv run pytest` 130 项通过、1 项 Windows 下 Linux `/proc` 专用测试跳过；`python scripts/security_scan.py` 通过。

## 2026-07-14 清理候选大文件不显示修复

- 针对“页面显示清理候选为空，但 `/tmp` 或 Downloads 中实际存在大于 10 MB 的 `.msi` 测试文件”的反馈，已定位关键原因：候选分类阶段会额外调用 `open_file_lookup` 判断文件是否被占用；当目标机未安装 `/usr/bin/lsof` 或占用检测能力不可用时，旧逻辑将状态标记为 `OPEN_FILE_STATE_UNKNOWN` 并排除候选，导致大文件被扫描到也不展示。
- 已为 `open_file_lookup` 增加 Linux `/proc/*/fd` 只读回退：缺少 `lsof` 时通过 inode/device 匹配打开文件的进程，不引入通用 Shell、不执行写操作、不放宽路径白名单。
- 已调整清理分类策略：普通日志在占用状态未知时仍失败关闭；但位于 `Downloads`、`.cache`、`tmp/temp` 等低风险目录中的 `.msi/.iso/.zip/.rpm/.deb/.exe` 等一次性下载/临时文件，即使占用检测暂不可用，也会先展示为“可处理候选”，执行删除前仍会重新校验路径、大小、快照哈希和占用状态。
- 新增测试覆盖：无 `lsof` 时 `/proc` 回退、占用状态未知时 Downloads 中 `.msi` 仍进入候选、普通日志 UNKNOWN 仍拒绝。
- 本轮真实回归：`uv run ruff check backend mcp_server` 通过；`uv run mypy backend mcp_server` 通过；`uv run pytest` 130 项通过、1 项 Windows 下 Linux `/proc` 专用测试跳过；`python scripts/security_scan.py` 通过。

## 2026-07-14 运维执行型交互文案与诊断结果说明优化

- 针对“页面过于像只读/安全演示、用户不知道如何删除”的反馈，已将前端导航与状态文案收敛为常规运维表达：`READ_ONLY` 在页面显示为“诊断模式”，`CONTROLLED_EXECUTION` 显示为“运维执行模式”；“安全审批中心”改为“风险确认中心”，“受控操作台”改为“运维操作台”。
- 智能运维对话的清理候选按钮从“申请清理”改为“选择并清理”，普通诊断模式下提示“已列出候选，删除需确认”；后端诊断摘要不再使用“只读诊断/READ_ONLY 下”这类比赛实现语言，改为“诊断完成、未执行删除/重启/配置修改”。
- `source` 字段展示继续中文化：系统快照、磁盘用量扫描、大文件扫描、进程列表、服务状态、服务日志、监听端口、网络配置、安全基线巡检、配置漂移检查等，避免页面直接暴露英文枚举。
- 安全巡检页面说明已补充真实检查范围：系统快照、磁盘阈值、服务状态、监听端口、僵尸进程、procfs/systemctl/journalctl 可用性和工具注册完整性；异常仍由确定性规则生成事件。
- 删除边界没有被放宽：当前实现支持发现候选并从候选发起清理流程；真正删除仍必须进入运维执行模式，经过预检查、风险确认、备份、执行、验证和审计。对于 `/tmp` 中由 root/vmuser 创建的文件，若服务账号无删除权限，仍需要后续新增固定白名单清理代理，不能降级为通用 Shell 或直接 root API。
- 本轮真实回归：`npm run type-check` 通过；`npm run build` 通过（仅 Vite chunk 体积提示）；`python scripts/security_scan.py` 通过；`uv run ruff check backend mcp_server` 通过；`uv run mypy backend mcp_server` 通过；`uv run pytest` 128 项通过，保留 Starlette TestClient 第三方弃用警告。

## 2026-07-14 VM `/tmp` 清理候选不可见修复

- 针对“测试 `.msi` 放在 `/tmp`，页面显示扫描 `/tmp` 但没有识别到”的反馈，已定位根因：`kylin-guard.service` 原先设置 `PrivateTmp=true`，systemd 会给后端服务创建隔离的私有 `/tmp`，导致服务看不到用户在宿主 VM 终端放入的 `/tmp/*.msi`。
- 已将 API 服务单元改为 `PrivateTmp=false`，使只读 MCP 工具能看到宿主机真实 `/tmp`，从而完成磁盘空间诊断和安全清理候选发现；这不放开写操作，不引入通用 Shell，也不绕过审批。
- 安全边界保持不变：READ_ONLY 只采集 `/tmp` 元数据和列出候选；真正删除仍必须在 `CONTROLLED_EXECUTION` 下经过 dry-run、人工审批、备份、执行后验证和审计。
- `scripts/release_audit.py` 新增 `PrivateTmp=false` 检查，防止后续部署单元回退导致 `/tmp` 不可见。
- VM 更新后需要重新安装/覆盖 systemd unit，并执行 `systemctl daemon-reload && systemctl restart kylin-guard`；仅 `git pull` 不会自动改变已安装的 `/etc/systemd/system/kylin-guard.service`。

## 2026-07-14 智能运维对话意图路由与清理候选实用性修复

- 针对“查询网络状态”误返回系统快照、CPU/磁盘信息的问题，已重写 Agent 规划器的确定性中文关键词路由：网络状态类问题固定采集 `network_config_snapshot` 与 `network_socket_list`，带端口号的问题继续路由到 `port_owner_lookup`，不再被“占用”等泛词误判为磁盘问题。
- 针对“分析磁盘空间不足并列出安全候选清理”识别不到 `/tmp`、用户 `Downloads/.cache/tmp` 中测试大文件的问题，清理分类器新增安装包与归档包后缀支持：`.msi`、`.iso`、`.zip`、`.tar/.tar.gz/.tgz`、`.7z`、`.rar`、`.rpm`、`.deb`、`.apk`、`.dmg`、`.pkg`、`.exe`。
- 位于低风险目录（`Downloads`、`download`、`.cache`、`cache`、`tmp`、`temp`）中的上述临时/下载类大文件，可立即作为“安全候选清理”展示，不再必须等待 7 天保留期；但敏感命名（如 secret/token/password/credential/private-key/id_rsa）和审计/数据库/WAL/binlog 等仍会被确定性拒绝。
- 安全边界保持不变：READ_ONLY 只扫描、诊断和列候选；真正删除仍必须在 `CONTROLLED_EXECUTION` 下由用户从候选发起 dry-run、人工审批、备份、执行后验证和审计，不允许 LLM 直接删除。
- 网络诊断结果页新增结构化结论：显示网络地址、路由、DNS 与监听记录数量，并给出“带端口号继续定位”的建议，不再落到通用系统健康快照。
- 本轮真实回归：`pytest -q` 128 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。仅保留 Starlette TestClient 第三方弃用警告，不影响功能。

## 2026-07-14 磁盘诊断默认根路径与清理候选双工具修复

- 针对页面输入“分析当前磁盘占用，给出根因和可清理候选”仍显示扫描 `/opt/kylin-guard` 的问题，已修复真实中文确定性路由：磁盘占用默认强制使用 `disk_usage_scan(path="/")`，不再由模型或服务工作目录决定扫描路径。
- 对同时包含“磁盘占用”和“可清理候选”的问题，计划会同时包含 `disk_usage_scan(path="/")` 与 `large_file_scan(path="__cleanup_roots__", min_bytes=10000000, limit=50)`；如果在线 LLM 返回 `/opt/kylin-guard` 或 `.`，服务端会在执行前规范化为安全固定参数。
- 清理候选分析已改为读取 `large_file_scan` 对应证据，而不是默认取第一条证据；诊断摘要会同时展示磁盘使用率、受控清理根、大文件数量和安全可清理候选数量。
- 安全边界保持不变：READ_ONLY 只诊断和列候选；删除仍必须进入 `CONTROLLED_EXECUTION`、dry-run、人工审批、备份、执行后验证和审计。
- 本轮真实回归：新增磁盘/清理规划测试通过；规划相关 15 项测试通过；全量 `pytest -q` 125 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 登录用户 Home 低风险目录显式扫描

- 针对“默认登录用户是 `vmuser` 或其他用户时，是否应扫描其 Home 子目录”的反馈，已新增 `KYLIN_GUARD_USER_HOME_SCAN_PATHS` 配置；后端会优先扫描显式配置的登录用户 Home 或已绑定低风险子目录，再尝试枚举 `/home`，因此 `/home` 无权限时不再丢失显式目标或返回 500。
- `deploy/install.sh` 会在源码目录位于 `/home/<user>/...` 时自动推断登录用户 Home，并写入 `/etc/kylin-guard/secrets.env`：`/home/<user>/.cache`、`/home/<user>/Downloads`、`/home/<user>/tmp`；已有配置不会被覆盖。
- systemd 仍保留 `ProtectHome=true`，安装脚本只额外创建 `20-user-home-scan.conf`，通过 `BindReadOnlyPaths` 只读绑定上述低风险子目录，不开放整个 `/home/<user>`，也不开放 `.ssh`、`.gnupg`、keyrings 等敏感目录。
- 安全边界保持不变：READ_ONLY 只分析和展示候选；删除仍必须进入 `CONTROLLED_EXECUTION`、dry-run、人工审批、备份、执行后验证和审计。
- 本轮真实回归：针对性 8 项用户目录扫描测试通过；全量 `pytest -q` 123 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 `/home` 无权限枚举安全降级

- 针对 VM 日志中的 `PermissionError: [Errno 13] Permission denied: '/home'`，已修复 `user_home_scan_roots()`：当服务账号无法枚举 `/home` 时安全降级为空用户目录扫描结果，不再让 Agent/MCP 接口返回 500。
- 该修复解释了“我用 root 跑 git/安装但页面仍报错”的原因：systemd 后端服务实际以 `kylin-guard` 等最小权限账号运行，不能假设拥有 root 对 `/home` 的遍历权限。
- 安全边界保持不变：不会为了修复 500 而扩大 `/home` 权限；如确需扫描用户低风险目录，应由部署侧显式授予服务账号读取 `.cache`、`Downloads`、`tmp` 的最小权限。
- 本轮真实回归：相关 7 项测试通过；全量 `pytest -q` 118 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 MCP 工具自检错误展示修复

- 针对页面点击 MCP 功能显示 `Internal Server Error` 的反馈，已调整 `/api/v1/mcp/tools/{tool_name}/test`：工具自检失败不再转换成 HTTP 422/500，而是以 HTTP 200 返回标准 `ToolResult`，由页面展示 `status=FAILED`、`error_code` 和 `warnings`。
- 该修复用于区分“页面/接口异常”和“目标机缺少某个只读能力或工具参数不满足”，不会把失败伪装成成功，也不改变任何执行权限。
- 写操作边界未变化：该接口仍只是 MCP 只读/自检入口，不新增通用 Shell，不执行状态变更。
- 本轮真实回归：针对性 27 项测试通过；全量 `pytest -q` 117 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 常见运维场景 MCP 覆盖扩展

- 在不引入通用 Shell、不放宽写权限的前提下，MCP 只读工具从 14 个扩展到 21 个，新增 `memory_snapshot`、`filesystem_inventory`、`network_config_snapshot`、`package_inventory`、`scheduled_task_inventory`、`login_audit`、`kernel_log_query`。
- 新增场景覆盖内存/Swap、挂载点与 inode、路由/网卡/DNS、RPM 软件包、cron/systemd timer、最近登录审计、内核 warning 日志；所有输出继续脱敏、截断并标记为 `UNTRUSTED_DATA`。
- 规则降级规划已支持中文自然语言路由：内存、文件系统/inode、DNS/路由、软件包、计划任务、登录审计、内核告警等问题会命中对应 MCP Tool；LLM 仍只能选择注册工具，不能直接执行命令。
- `mcp_server/registry.py` 和 `backend/app/agent/planning.py` 已清理历史乱码，MCP 工具标题、描述和规则兜底摘要恢复为正常中文。
- 写操作边界未变化：删除、重启、配置更新、进程终止等仍必须走 `CONTROLLED_EXECUTION`、dry-run、人工审批、备份、执行后验证和审计。
- 本轮真实回归：针对性 23 项测试通过；全量 `pytest -q` 116 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 用户低风险目录扫描默认开启

- 按用户要求，`user_home_scan_enabled` 默认值已从 `false` 改为 `true`；`.env.example` 与 `config/app.example.yaml` 同步改为 `KYLIN_GUARD_USER_HOME_SCAN_ENABLED=true` / `user_home_scan_enabled: true`。
- 安全边界保持不变：默认开启只会纳入实际存在的 `/home/<user>/.cache`、`/home/<user>/Downloads`、`/home/<user>/tmp`，不会扫描整个 `/home`，也不会纳入 `.ssh`、`.gnupg`、keyrings 等敏感目录；LLM 和普通对话仍不能临时扩大扫描范围。
- 删除边界未放宽：READ_ONLY 仍只分析和展示候选；真正删除仍必须在 `CONTROLLED_EXECUTION` 下经过 dry-run、人工审批、备份、执行后验证和审计。
- 本轮真实回归：针对性 15 项测试通过；全量 `pytest -q` 114 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 系统级只读磁盘诊断与清理边界拆分

- 针对“分析磁盘占用只扫描 `/opt/kylin-guard`”的问题，已将规则降级计划中的 `disk_usage_scan` 默认参数改为 `path="/"`；READ_ONLY 下磁盘容量诊断默认面向系统根文件系统，而不是服务工作目录。
- MCP 读范围与清理候选范围已拆分：`allowed_roots` 可包含 `/` 以支持系统级只读容量/元数据诊断；`cleanup_roots` 独立用于 `large_file_scan("__cleanup_roots__")` 和清理候选分类，默认仍只覆盖受控清理根、日志/临时目录和用户低风险目录。
- 只读根扩大后同步加入 protected path 防护，`/etc/shadow`、`/etc/gshadow`、`/root`、`/boot`、`/proc`、`/sys`、`/dev`、`/run`、`/var/lib` 等路径不会因位于 `/` 下而被显式文件查询或进入清理候选。
- 删除等状态变更边界未放宽：READ_ONLY 只诊断和展示候选；真正删除仍必须在 `CONTROLLED_EXECUTION` 下走 dry-run、人工审批、备份、执行后验证和审计。
- 本轮真实回归：针对性 32 项测试通过；全量 `pytest -q` 114 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 用户目录低风险扫描开关

- 用户低风险目录扫描开关 `user_home_scan_enabled` 已改为默认 `true`；`.env.example` 同步提供 `KYLIN_GUARD_USER_HOME_SCAN_ENABLED=true`。该开关仍只能由部署配置或 Secret 环境关闭/开启，LLM 和普通对话不能临时扩大扫描范围。
- 开启后只扩展实际存在的 `/home/<user>/.cache`、`/home/<user>/Downloads`、`/home/<user>/tmp`，不会扫描整个 `/home`，也不会纳入 `.ssh`、`.gnupg`、`.config`、keyrings 等敏感目录；子目录配置拒绝绝对路径和 `..` 穿越。
- MCP 只读扫描和生产受控清理共用同一套服务端根目录扩展逻辑：`read_only_scan_roots()` 供 MCP Provider 使用，`controlled_cleanup_roots()` 供生产 `safe_log_cleanup` 使用，保持“能发现”和“可受控清理”的边界一致。
- `backend/tests/test_user_home_scan_config.py` 覆盖默认开启、不扫描整个 `/home`、只纳入低风险既有子目录、不会纳入 `.ssh` 以及拒绝 `../escape` 配置。
- 本轮真实回归：针对性 14 项测试通过；全量 `pytest -q` 114 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过。

## 2026-07-14 受控执行型运维 Agent 方向优化

- 已按“受控执行型运维 Agent”方向收敛前端信息架构：移除“安全演示闭环”菜单与路由入口，保留智能运维对话、受控操作台、安全审批中心、任务时间线、MCP 工具、安全巡检、事件、漂移、知识库和审计等真实运维入口。
- 清理分析从单一工作目录升级为受控清理根集合：默认只读扫描实际存在的 `Path.cwd()`、`/var/log`、`/tmp`、`/var/tmp`；真正生产清理配置同步加入 `/var/log/kylin-guard-managed`、`/var/log`、`/tmp`、`/var/tmp`，同时继续保护 `/etc`、`/root`、`/boot`、`/proc`、`/sys`、`/dev`、`/run`、`/var/lib`。`/tmp` 与 `/var/tmp` 仅作为受控候选扫描根，已在代码中显式标注 ruff S108 豁免原因。
- 智能运维对话中的清理候选表新增“申请清理”入口；在 `CONTROLLED_EXECUTION` 下，用户可从候选直接发起 `safe_log_cleanup` dry-run 与审批申请，并在同一任务页查看审批状态、领取已批准的一次性令牌并执行。READ_ONLY 下仍只分析不删除。
- 安全巡检从单点快照增强为多项只读基线：系统快照增加受控目录磁盘用量列表，基线检查包括固定工具注册、procfs、systemctl、journalctl、白名单服务状态、监听端口暴露线索和僵尸进程；事件派生会根据多目录磁盘阈值和基线 WARN 生成 Incident。
- 本轮真实回归：针对性 16 项测试通过；全量 `pytest -q` 112 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过；前端 `npm run type-check` 与 `npm run build` 通过。Vite 仍仅提示 Element Plus chunk 大小警告，不影响当前验收。

## 2026-07-14 LLM 接入说明与 SSH 服务意图修复

- 针对“询问 ssh 服务有没有开启却回答 nginx 当前未发现异常”的反馈，已修复离线/不可用 LLM 兜底规划：`ssh`、`sshd` 和服务类问题会进入 `service_status` 路由，其中 SSH 统一规范化为 `sshd`，并追加 `journal_query(unit=sshd)` 采集最近日志，不再默认套用 nginx。
- 只读 MCP Provider 的默认服务查询白名单新增 `sshd`，用于 `READ_ONLY` 下安全查询 SSH 服务状态；生产受控写执行、sudoers、固定执行代理和 `service_restart` 白名单仍保持 nginx-only，未扩大任何写权限。
- 前端智能运维对话示例新增“ssh 服务有没有开启”，便于在官方 VM 页面直接复现；DeepSeek/OpenAI-compatible Provider 仍通过环境变量接入，未把任何 API Key 写入仓库。
- 本轮真实回归：`pytest -q` 112 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；`security_scan.py` 通过；前端 `npm run type-check` 与 `npm run build` 通过。Vite 仍仅提示 Element Plus chunk 大小警告，不影响功能。

## 2026-07-14 智能运维对话结论闭环修复

- 针对 VM 页面验收反馈，已将“智能运维对话”从内部字段展示改为面向运维人员的问答式闭环：页面顶部先显示 `Agent 结论`，包括正常/关注/异常等级、直接回答、关键发现和建议动作，再展示工具计划、清理候选、根因、决策链、标准化证据和原始工具回执。
- 后端新增 `diagnosis` 结构化结果：磁盘类问题直接说明扫描路径、使用率和可用空间；清理类问题说明发现的大文件数量、可安全清理候选数量及未入选原因；服务类问题直接判断 `active/failed/inactive/unknown`；CPU/进程类问题列出按累计 CPU ticks 排序的进程线索；端口类问题返回端口监听匹配数；L4 请求明确显示“已阻断且未调用工具”。
- 修复中文路由优先级和默认参数：`nginx` 服务问题默认调用 `service_status(service=nginx)` 并追加 `journal_query(unit=nginx)`；`8080 端口由哪个进程占用` 优先路由到 `port_owner_lookup(port=8080)`；清理类问题调用 `large_file_scan(path=., min_bytes=10000000, limit=50)`；工具参数为空时页面显示“无需参数”。
- `process_list` 在 Linux `/proc` 只读路径中补充 `cpu_ticks` 和 `rss_pages`，按累计 CPU ticks 排序，避免 CPU 类问题只显示抽象百分比。该实现不调用任意 Shell，不引入 `shell=True`，不改变 READ_ONLY 默认安全边界。
- 本轮真实回归：`pytest -q` 111 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；前端 `npm run type-check` 与 `npm run build` 通过；`security_scan.py` 通过。Vite 仍仅提示 Element Plus chunk 大小警告，不影响功能。

## 2026-07-14 智能运维对话可解释性与中文路由修复

- 针对 VM 页面验收反馈，已重构“智能运维对话”结果页：示例气泡明确作为输入模板；新增本次对话结果、计划摘要、公开理由、工具调用计划、原始工具回执；标准化证据和清理候选均可点击“查看”打开详情抽屉。
- 根因候选百分比已在页面说明为 RCA 置信度，来源于异常程度、证据类型和时间相关性，不代表执行进度；清理候选为空时新增明确解释，包括非清理意图、无允许目录大旧日志、未达到大小/保留期阈值、保护路径和 READ_ONLY 不执行删除。
- 修复后端中文关键字路由与中文安全拦截乱码问题：`清理/垃圾/旧日志/缓存` 路由到 `large_file_scan`，`磁盘/空间` 路由到 `disk_usage_scan`，`进程/僵尸` 路由到 `process_list`，`端口` 路由到 `network_socket_list`；中文“忽略/绕过/读取密钥/显示系统提示词”等请求恢复 L4 阻断。
- 修复后端公开决策链、RCA 推荐动作和前端状态映射中文乱码；仍不保存或展示模型隐藏思维，仅展示结构化公开决策链和工具证据。
- 本轮真实回归：相关后端测试 30 项通过；全量 `pytest -q` 110 项通过；`ruff check backend mcp_server scripts` 通过；`mypy backend mcp_server` 通过；前端 `npm run type-check` 与 `npm run build` 通过；`security_scan.py` 通过。

## 2026-07-14 LoongArch 前端访问与任务页布局修复

- LoongArch VM 已完成依赖构建、后端健康接口和 Nginx 启动；首页 500 定位为 Nginx 用户无法 `stat /opt/kylin-guard/frontend/index.html`，根因是 `/opt/kylin-guard` 目录最小权限阻止 Nginx 穿越目录读取静态文件。
- 已在 `deploy/install.sh` 中补充最小 ACL：若存在 `nginx` 用户，仅授予其穿越 `$APP_ROOT` 与只读访问 `$APP_ROOT/frontend` 的权限，不开放后端代码目录、数据库目录、Secret 或受控执行代理。
- 智能运维对话执行后页面横向移动定位为长证据、长任务字段、时间线和表格内容可能撑宽布局；已在全局样式和任务页样式中增加 `minmax(0,1fr)`、`min-width:0`、横向溢出保护和长文本换行，避免底部横向滚动条反复出现。
- 以上变更只影响前端展示和 Nginx 静态文件读取权限，不改变默认 `READ_ONLY`、后端安全护栏、审批、审计、MCP Tool 或受控执行边界。

## 2026-07-14 LoongArch rpds 1.1.1 继续收敛

- 官方麒麟 LoongArch VM 新错误显示 `rpds-py==0.27.1` 的源码构建会下载 Rust crate `rpds v1.1.1`，该 crate 同样要求 Cargo `edition2024`，目标机 Cargo 1.82.0 无法解析，导致 `metadata-generation-failed`。
- 已将运行依赖继续收敛为 `rpds-py>=0.24,<0.25`，当前部署导出锁定为 `rpds-py==0.24.0`；该版本位于 `rpds v1.1.1` 之前，用于避开 LoongArch 源码构建时的 `edition2024` 链路。`jsonschema` 随约束回落到 `4.25.1`，仍满足 MCP SDK 依赖要求。
- 部署 requirements 继续剥离未使用的 `cryptography/cffi/pycparser`，`deploy/install.sh` 继续使用 `pip install --no-deps --require-hashes`，`deploy/build-constraints.txt` 继续约束构建后端 `maturin==1.9.4`。
- 本轮真实回归：`uv run pytest -q` 110 项通过；`uv run ruff check backend mcp_server scripts` 通过；`uv run mypy backend mcp_server` 通过（88 个源文件）；`uv run python scripts/security_scan.py` 通过（196 个文本/源码文件）；`uv run python scripts/validate_phase0.py` 通过；干净 Python 3.11 部署 requirements 冒烟通过，可导入 `FastMCP`、后端 app 并列出 14 个 Tool。
- 该修复只影响 LoongArch 源码构建依赖收敛，不改变默认 `READ_ONLY`、安全护栏、审批、审计、MCP Tool 行为或生产受控执行边界；LoongArch 官方 VM 仍需以用户重新拉取后的安装结果为准。

## 2026-07-14 LoongArch rpds-py 规避 archery 1.2.2

- 官方麒麟 LoongArch VM 继续在 `archery 1.2.2` 处失败，经源码检查确认来源为 `rpds-py`：`rpds-py>=0.28.0` 的 `Cargo.lock` 引入 `archery 1.2.2`，而该 crate 要求 Cargo `edition2024`。
- 已将运行依赖显式约束为 `rpds-py>=0.27.1,<0.28`，重新锁定并导出部署依赖；`rpds-py==0.27.1` 使用 `archery 1.2.1`，避开 `edition2024`。部署 requirements 继续剥离未使用的 `cryptography/cffi/pycparser`，并保留 `--no-deps` 安装策略。
- 本轮验证：`pytest -q` 110 项通过；`ruff`、`mypy`、`security_scan.py`、`validate_phase0.py` 均通过；干净 Python 3.11 部署安装冒烟通过，安装列表包含 `rpds-py==0.27.1` 且可导入后端 app、FastMCP 并列出 14 个 Tool。
- 该修复只收敛 LoongArch 源码构建依赖，不改变安全边界、默认 `READ_ONLY`、审批、审计或 Tool 行为。

## 2026-07-14 LoongArch maturin 约束修正为 1.9.4

- 官方麒麟 LoongArch VM 新错误显示源码包构建依赖要求 `maturin>=1.9,<2.0`，上一版 `maturin==1.8.7` 约束过低，导致 pip 构建依赖解析冲突。
- 已检查 `maturin 1.9.0` 至 `1.9.4` 源码 `Cargo.toml`，均声明 `edition = "2021"`、`rust-version = "1.74"`，可避开 Cargo 1.82 不支持 `edition2024` 的问题；因此将 `deploy/build-constraints.txt` 修正为 `maturin==1.9.4`。
- 该变更只影响 pip 构建隔离环境中的 build backend 版本，不改变运行时依赖、安全策略、默认 `READ_ONLY` 或 MCP Tool 行为。

## 2026-07-14 LoongArch maturin 构建后端约束

- 官方麒麟 LoongArch VM 新错误为构建 `maturin` 自身时触发 Cargo `edition2024`，来源是 pip 构建隔离环境为 `pydantic-core`/`rpds-py` 等源码包临时拉取了过新的 build backend。
- 新增 `deploy/build-constraints.txt`，固定 `maturin==1.8.7`；`deploy/install.sh` 通过 `PIP_CONSTRAINT` 将该约束传递给 pip 的构建隔离环境，同时继续使用 `--no-deps --require-hashes` 安装运行时锁定依赖。
- 本地验证：`pytest -q` 110 项通过；`ruff check backend mcp_server scripts`、`mypy backend mcp_server`、`security_scan.py`、`validate_phase0.py` 均通过；干净 Python 3.11 部署依赖安装冒烟可导入 `FastMCP`、后端 app 并列出 14 个 Tool。
- 该修复仅约束构建工具链，不改变运行模式、安全护栏、审批、审计或 MCP Tool 注册逻辑；LoongArch 真机安装仍需以官方 VM 最新结果为准。

## 2026-07-14 LoongArch 部署专用依赖剥离 crypto

- 官方麒麟 LoongArch VM 仍在 `archery 1.2.2` 处失败，确认单纯降级 `cryptography` 不足以规避 MCP SDK `pyjwt[crypto]` 的源码构建链。
- 已改为部署专用策略：`deploy/requirements.txt` 剥离 `cryptography`、`cffi`、`pycparser`，保留 `pyjwt==2.13.0`；`deploy/install.sh` 使用 `pip install --no-deps --require-hashes`，防止 pip 根据 `mcp` 元数据再次拉取未使用的 JWT crypto 扩展。项目自身会话认证不使用 JWT/cryptography，MCP 当前仅使用 FastMCP stdio 和本地 Tool registry。
- 已移除安装脚本中不再需要的 libffi-devel 前置检查；LoongArch 仍需 `python3-devel gcc make rust cargo` 以应对 pydantic-core 等源码构建。
- 本地干净 Python 3.11 部署冒烟通过：使用剥离后的 requirements 和 `--no-deps --require-hashes` 安装后，可导入 `FastMCP`、`backend.app.main`，并列出 14 个 Tool。完整回归：`pytest -q` 110 项通过，`ruff`、`mypy`、`security_scan.py`、`validate_phase0.py` 均通过。
- 该策略为 LoongArch 部署兼容性取舍，不改变默认 `READ_ONLY`、安全护栏、审批、审计或受控执行边界；如未来启用 MCP 远程 OAuth/JWT 验签能力，必须重新引入经过 LoongArch 验证的加密依赖或离线 wheelhouse。

## 2026-07-14 LoongArch Rust 依赖继续收敛

- 官方麒麟 LoongArch VM 继续在 `archery 1.2.2` 处失败，说明 `cryptography==42.0.8` 源码构建仍会触发不兼容 Cargo 1.82.0 的 Rust crate。
- 已将部署依赖进一步收敛到 `cryptography==38.0.4`、`cffi==1.17.1`，继续保持 `mcp==1.28.1` 与 `pydantic-core==2.33.2`；该项目自身认证会话不依赖 JWT/cryptography 功能，cryptography 仅由 MCP SDK 的 `pyjwt[crypto]` 链路引入。
- 本轮真实回归：`uv run pytest -q` 110 项通过（仅 Starlette TestClient 第三方弃用警告）；`uv run ruff check backend mcp_server scripts`、`uv run mypy backend mcp_server`、`uv run python scripts/security_scan.py`、`uv run python scripts/validate_phase0.py` 均通过。
- 若 LoongArch 仍在 cryptography 源码构建失败，下一步应改为部署专用 requirements 彻底剥离 MCP 未使用的 JWT crypto 依赖或准备离线 wheelhouse，而不是默认升级系统 Rust。

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

