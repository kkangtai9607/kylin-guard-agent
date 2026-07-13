# 受控执行启用手册

默认安装只运行 `READ_ONLY`。不得将 API 服务改为 root，也不得添加任意参数、解释器或 Shell 的 sudoers 规则。

受控执行采用以下固定边界：

```text
kylin-guard API（无 sudo、NoNewPrivileges=true）
  -> /run/kylin-guard/executor.sock（仅本机、Peer UID 校验）
  -> kylin-guard-exec（固定请求校验）
  -> sudo 固定 root helper（固定参数）
  -> /usr/bin/systemctl restart nginx
```

当前可启用的唯一生产动作是白名单 `nginx` 重启。其他生产写操作继续保持禁用，直至分别拥有同等级的固定辅助程序、独立验证和回滚演练记录。

管理员必须在隔离的目标机逐项完成：

1. 执行 `visudo -cf deploy/kylin-guard.sudoers`；确认该文件只有一个固定 helper 和固定参数。
2. 以 root 安装 sudoers：`install -m 0440 -o root -g root deploy/kylin-guard.sudoers /etc/sudoers.d/kylin-guard`，并再次使用 `visudo -cf /etc/sudoers.d/kylin-guard` 校验。
3. 启动代理：`systemctl enable --now kylin-guard-exec`；确认 Socket 的 owner 为 `kylin-guard-exec:kylin-guard`、权限为 `0660`。
4. 代理必须能原子消费审批记录，但 API 仍是唯一的常规数据库写入者；执行代理 systemd 单元只获得 `/run/kylin-guard` 和 `/opt/kylin-guard/data` 两个可写路径。麒麟 V11 的 sudo/PAM 需要保留默认 capability bounding set 才能进入精确 sudoers 规则；安全性由非 root 执行账号、Socket peer UID、固定 helper/参数、无 Shell 和独立审批核验共同保证。使用 ACL 仅向 `kylin-guard-exec` 授予数据目录和 SQLite 文件所需的最小读写权限：`setfacl -m u:kylin-guard-exec:rwx /opt/kylin-guard/data`、`setfacl -m d:u:kylin-guard-exec:rwx /opt/kylin-guard/data`、`setfacl -m u:kylin-guard-exec:rw /opt/kylin-guard/data/kylin_guard.db`。若目标机缺少 POSIX ACL 能力，不得启用生产受控执行。
5. 保持 API 服务为非 root，确认 `systemctl show kylin-guard -p User -p NoNewPrivileges` 输出 `User=kylin-guard`、`NoNewPrivileges=yes`。
6. 在 `CONTROLLED_EXECUTION` 前，完成独立审批、dry-run、实际重启、状态验证和审计链校验。任何一步失败立即切回 `READ_ONLY` 并禁用执行代理。

运行模式不是单个任务参数，也不能由 LLM 或 API 请求提升。
