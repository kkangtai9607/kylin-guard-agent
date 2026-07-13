#!/usr/bin/env bash
set -euo pipefail

URL=${KYLIN_GUARD_HEALTH_URL:-http://127.0.0.1:8000/api/v1/health}
python3 - "$URL" <<'PY'
import json, sys, urllib.request
url = sys.argv[1]
with urllib.request.urlopen(url, timeout=5) as response:
    payload = json.load(response)
if response.status != 200 or payload.get("data", {}).get("status") != "ok":
    raise SystemExit(1)
print("KylinGuard healthcheck: ok")
PY
