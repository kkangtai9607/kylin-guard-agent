from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    requirements = (ROOT / "deploy/requirements.txt").read_text(encoding="utf-8")
    if re.search(r"(?:[A-Za-z]:\\|file://|\.\./)", requirements):
        errors.append("requirements contains a local or relative path")
    service = (ROOT / "deploy/kylin-guard.service").read_text(encoding="utf-8")
    for required in ("User=kylin-guard", "NoNewPrivileges=true", "ProtectSystem=strict"):
        if required not in service:
            errors.append(f"systemd hardening missing: {required}")
    install = (ROOT / "deploy/install.sh").read_text(encoding="utf-8")
    if "uname -m" not in install or "/etc/os-release" not in install:
        errors.append("installer lacks platform detection")
    if "alembic.ini" not in install:
        errors.append("installer does not copy alembic.ini")
    if "/etc/sudoers.d" in install:
        errors.append("first READ_ONLY install must not enable sudoers")
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for required in (".venv/", "frontend/node_modules/", "frontend/dist/"):
        if required not in ignored:
            errors.append(f"submission exclusion missing: {required}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Release static audit passed; target-platform runtime verification remains required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
