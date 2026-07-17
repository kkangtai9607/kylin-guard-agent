# 受控执行启用手册

默认安装运行管理员运维模式，但 API 服务仍保持非 root。不得将 API 服务改为 root，也不得添加任意参数、解释器或 Shell 的 sudoers 规则。

受控执行采用以下固定边界：

```text
kylin-guard API（无 sudo、NoNewPrivileges=true）
  -> /run/kylin-guard/executor.sock（仅本机、Peer UID 校验）
  -> kylin-guard-exec（固定请求校验）
  -> sudo 固定 root helper（固定入口）
  -> /usr/bin/systemctl restart nginx 或白名单清理候选备份/删除/回滚
```

当前可启用的生产特权动作是白名单 `nginx` 重启，以及已冻结候选的 `safe_log_cleanup/cleanup_rollback`。清理 helper 会重新校验 candidate_id、路径白名单、保护路径、文件类型、inode/device/size、snapshot_hash、备份和回滚规则；仍不接受任意路径命令或 Shell。

管理员必须在隔离的目标机逐项完成：

1. 执行 `visudo -cf deploy/kylin-guard.sudoers`；确认该文件只有固定 helper 入口，没有 Shell、解释器通配或任意可执行文件。
2. 以 root 安装 sudoers：`install -m 0440 -o root -g root deploy/kylin-guard.sudoers /etc/sudoers.d/kylin-guard`，并再次使用 `visudo -cf /etc/sudoers.d/kylin-guard` 校验。
3. 启动代理：`systemctl enable --now kylin-guard-exec`；确认 Socket 的 owner 为 `kylin-guard-exec:kylin-guard`、权限为 `0660`。
4. 代理必须能原子消费审批记录，但 API 仍是唯一的常规数据库写入者；执行代理 systemd 单元只获得 `/run/kylin-guard`、`/opt/kylin-guard/data` 和 `/var/lib/kylin-guard/backups` 三个可写路径。麒麟 V11 的 sudo/PAM 需要保留默认 capability bounding set 才能进入精确 sudoers 规则；安全性由非 root 执行账号、Socket peer UID、固定 helper/参数、无 Shell 和独立审批核验共同保证。使用 ACL 仅向 `kylin-guard-exec` 授予数据目录和 SQLite 文件所需的最小读写权限：`setfacl -m u:kylin-guard-exec:rwx /opt/kylin-guard/data`、`setfacl -m d:u:kylin-guard-exec:rwx /opt/kylin-guard/data`、`setfacl -m u:kylin-guard-exec:rw /opt/kylin-guard/data/kylin_guard.db`。若目标机缺少 POSIX ACL 能力，不得启用生产受控执行。
5. 保持 API 服务为非 root，确认 `systemctl show kylin-guard -p User -p NoNewPrivileges` 输出 `User=kylin-guard`、`NoNewPrivileges=yes`。
6. 完成独立审批、dry-run、实际清理/重启、状态验证和审计链校验。任何固定动作验证失败，应禁用对应动作或执行代理，不得降级为通用 Shell。

运行模式不是单个任务参数，也不能由 LLM 或 API 请求提升。
