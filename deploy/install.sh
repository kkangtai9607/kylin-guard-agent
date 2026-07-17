#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=${APP_ROOT:-/opt/kylin-guard}
SOURCE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [[ $(id -u) -ne 0 ]]; then echo "install requires root" >&2; exit 1; fi
architecture=$(uname -m)
case "$architecture" in x86_64|aarch64|loongarch64) ;; *) echo "unsupported architecture: $architecture" >&2; exit 1;; esac
if [[ ! -f /etc/os-release ]]; then echo "missing /etc/os-release" >&2; exit 1; fi
python_include=$(python3 - <<'PY'
import sysconfig
print(sysconfig.get_paths().get("include", ""))
PY
)
if [[ ! -f "$python_include/Python.h" ]]; then
  echo "missing Python development headers: $python_include/Python.h" >&2
  echo "Install build dependencies first, for example:" >&2
  echo "  yum install -y python3-devel gcc make rust cargo" >&2
  exit 1
fi
if ! command -v gcc >/dev/null 2>&1; then
  echo "missing gcc; install build dependencies first: yum install -y gcc make" >&2
  exit 1
fi

getent group kylin-guard >/dev/null || groupadd --system kylin-guard
id kylin-guard >/dev/null 2>&1 || useradd --system --gid kylin-guard --home "$APP_ROOT" --shell /usr/sbin/nologin kylin-guard
id kylin-guard-exec >/dev/null 2>&1 || useradd --system --gid kylin-guard --home "$APP_ROOT" --shell /usr/sbin/nologin kylin-guard-exec

infer_source_login_home() {
  case "$SOURCE_ROOT" in
    /home/*/*)
      local login_name
      login_name=$(printf '%s\n' "$SOURCE_ROOT" | cut -d/ -f3)
      printf '/home/%s\n' "$login_name"
      ;;
  esac
}

configure_user_home_scan() {
  local login_home
  login_home=$(infer_source_login_home || true)
  if [[ -z "$login_home" || ! -d "$login_home" ]]; then
    return
  fi

  local scan_paths=(
    "$login_home/.cache"
    "$login_home/Downloads"
    "$login_home/Download"
    "$login_home/downloads"
    "$login_home/downlaods"
    "$login_home/Desktop"
    "$login_home/Documents"
    "$login_home/tmp"
  )
  local scan_paths_csv
  scan_paths_csv=$(IFS=,; printf '%s' "${scan_paths[*]}")

  install -d -m 0750 -o root -g kylin-guard /etc/kylin-guard
  if [[ ! -f /etc/kylin-guard/secrets.env ]]; then
    install -m 0640 -o root -g kylin-guard /dev/null /etc/kylin-guard/secrets.env
  fi
  if ! grep -q '^KYLIN_GUARD_USER_HOME_SCAN_PATHS=' /etc/kylin-guard/secrets.env; then
    printf 'KYLIN_GUARD_USER_HOME_SCAN_PATHS=%s\n' "$scan_paths_csv" >> /etc/kylin-guard/secrets.env
  fi

  install -d -m 0755 -o root -g root /etc/systemd/system/kylin-guard.service.d
  {
    printf '[Service]\n'
    printf 'BindReadOnlyPaths='
    local scan_path
    for scan_path in "${scan_paths[@]}"; do
      printf -- '-%s ' "$scan_path"
    done
    printf '\n'
  } > /etc/systemd/system/kylin-guard.service.d/20-user-home-scan.conf
}

install -d -m 0750 -o kylin-guard -g kylin-guard "$APP_ROOT" "$APP_ROOT/data"
install -d -m 0700 -o root -g root /var/lib/kylin-guard/backups
cp -a "$SOURCE_ROOT/backend" "$SOURCE_ROOT/mcp_server" "$SOURCE_ROOT/config" "$SOURCE_ROOT/pyproject.toml" "$SOURCE_ROOT/uv.lock" "$SOURCE_ROOT/alembic.ini" "$APP_ROOT/"
install -d -m 0755 "$APP_ROOT/frontend"
cp -a "$SOURCE_ROOT/frontend/dist/." "$APP_ROOT/frontend/"

python3 -m venv "$APP_ROOT/.venv"
PIP_CONSTRAINT="$SOURCE_ROOT/deploy/build-constraints.txt" \
  "$APP_ROOT/.venv/bin/pip" install --no-cache-dir --no-deps --require-hashes --requirement "$SOURCE_ROOT/deploy/requirements.txt"
chown -R root:kylin-guard "$APP_ROOT"
chown -R kylin-guard:kylin-guard "$APP_ROOT/data"
if command -v setfacl >/dev/null 2>&1; then
  if id nginx >/dev/null 2>&1; then
    setfacl -m u:nginx:--x "$APP_ROOT"
    setfacl -R -m u:nginx:rX "$APP_ROOT/frontend"
  fi
  setfacl -m u:kylin-guard-exec:rwx "$APP_ROOT/data"
  setfacl -m d:u:kylin-guard-exec:rwx "$APP_ROOT/data"
  setfacl -m u:kylin-guard-exec:rw "$APP_ROOT/data/kylin_guard.db" 2>/dev/null || true
fi
install -m 0644 "$SOURCE_ROOT/deploy/kylin-guard.service" /etc/systemd/system/kylin-guard.service
install -m 0644 "$SOURCE_ROOT/deploy/kylin-guard-exec.service" /etc/systemd/system/kylin-guard-exec.service
configure_user_home_scan
install -d -m 0755 -o root -g root /usr/local/lib/kylin-guard
install -m 0750 -o root -g root "$SOURCE_ROOT/deploy/kylin_guard_privileged.py" /usr/local/lib/kylin-guard/kylin_guard_privileged.py
systemctl daemon-reload
echo "Installed controlled operations runtime for $architecture. Privileged fixed-action broker remains disabled until explicitly enabled."
