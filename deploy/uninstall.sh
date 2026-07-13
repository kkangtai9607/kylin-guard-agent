#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=${APP_ROOT:-/opt/kylin-guard}
if [[ $(id -u) -ne 0 ]]; then echo "uninstall requires root" >&2; exit 1; fi
systemctl disable --now kylin-guard.service kylin-guard-exec.service 2>/dev/null || true
rm -f /etc/systemd/system/kylin-guard.service /etc/systemd/system/kylin-guard-exec.service /etc/sudoers.d/kylin-guard
rm -rf /usr/local/lib/kylin-guard
systemctl daemon-reload
if [[ "$APP_ROOT" != "/opt/kylin-guard" ]]; then echo "refusing nonstandard APP_ROOT removal" >&2; exit 1; fi
rm -rf -- "$APP_ROOT"
echo "Application removed; service accounts retained for auditability."
