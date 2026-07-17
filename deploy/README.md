# 麒麟 VM 首次迁移运行手册

首次迁移默认进入管理员“运维模式”（内部模式为 `CONTROLLED_EXECUTION`），并应在可恢复快照的干净测试 VM 中完成。系统不会提供任意 Shell；删除、重启、修改配置等写操作仍必须经过固定工具、候选校验、风险确认、备份、执行后验证和审计。

## 迁移前检查

在项目根目录执行：

```bash
python3 scripts/platform_probe.py
python3 scripts/release_audit.py
python3 scripts/security_scan.py
```

必须人工确认 `/etc/os-release`、`uname -m`、Python 3.10+、systemd、SQLite FTS5/WAL，以及 `ss`、`lsof`、`iostat`、`journalctl`、`systemctl` 的实际路径。缺失能力应记录为降级，不能伪装为已通过。

## 安装与启动

先构建前端，再以 root 从源码根目录安装：

```bash
cd frontend && npm ci && npm run type-check && npm run build && cd ..
bash deploy/install.sh
install -d -m 0750 -o root -g kylin-guard /etc/kylin-guard
install -m 0640 -o root -g kylin-guard /dev/null /etc/kylin-guard/secrets.env
systemctl enable --now kylin-guard
bash deploy/healthcheck.sh
```

麒麟 V11 自带 Nginx 默认站点时，不要同时加载另一个 `server_name _`。应将 `deploy/nginx-kylin-default.conf` 安装到 `/etc/nginx/default.d/kylin-guard.conf`，执行 `nginx -t` 成功后再重载；其他发行版可使用完整的 `deploy/nginx.conf`。

`/etc/kylin-guard/secrets.env` 仅允许保存环境注入项。首次启动至少保持：

```dotenv
KYLIN_GUARD_MODE=CONTROLLED_EXECUTION
KYLIN_GUARD_SNAPSHOT_SCHEDULER_ENABLED=false
KYLIN_GUARD_USER_HOME_SCAN_PATHS=/home/vmuser/.cache,/home/vmuser/Downloads,/home/vmuser/tmp
```

新 DeepSeek Key 应在提供商侧轮换后再注入；不得使用聊天中曾暴露的 Key。

## 运维模式验证

1. 先验证数据库迁移、API、前端、安全扫描和只读 MCP Tool。
2. 验证清理候选链路：扫描候选、创建风险确认、确认并执行、查看备份/验证/审计。
3. 再显式启用定时快照并观察数据库、日志和资源占用。
4. 服务重启等需要 root 的固定动作，只有在目标机逐项通过后，才人工审查并安装 `deploy/kylin-guard.sudoers` 并启动 `kylin-guard-exec`。
5. 若任一写操作验证失败，应保留运维模式但禁用对应固定动作，不得降级为通用 Shell 或 root API。

当前 Windows 主机的结果不能替代麒麟 V11 或 LoongArch 真机结论。
