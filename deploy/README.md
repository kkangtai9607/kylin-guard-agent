# 麒麟 VM 首次迁移运行手册

首次迁移只允许 `READ_ONLY`，并应在可恢复快照的干净测试 VM 中完成。安装脚本不会启用 sudoers，也不会打开生产写操作。

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
KYLIN_GUARD_MODE=READ_ONLY
KYLIN_GUARD_SNAPSHOT_SCHEDULER_ENABLED=false
KYLIN_GUARD_USER_HOME_SCAN_PATHS=/home/vmuser/.cache,/home/vmuser/Downloads,/home/vmuser/tmp
```

新 DeepSeek Key 应在提供商侧轮换后再注入；不得使用聊天中曾暴露的 Key。

## 分级启用

1. 先验证数据库迁移、API、前端、安全扫描和 14 个只读 MCP Tool。
2. 再在 `READ_ONLY` 下显式启用定时快照并观察数据库、日志和资源占用。
3. 在隔离 DEMO 资源验证审批、备份、验证和回滚。
4. 只有生产写适配器和固定参数在目标机逐项通过后，才可人工审查并安装 `deploy/kylin-guard.sudoers`。
5. 未完成上述验证前不得设置 `CONTROLLED_EXECUTION`。

当前 Windows 主机的结果不能替代麒麟 V11 或 LoongArch 真机结论。
