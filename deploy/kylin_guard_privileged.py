#!/usr/bin/env python3
"""Root-owned, fixed-argument helper. It intentionally exposes no generic command API."""

from __future__ import annotations

import subprocess
import sys

_RESTART = ("service_restart", "nginx")
_ROLLBACK = ("service_rollback", "nginx")
_SYSTEMCTL = "/usr/bin/systemctl"


def main(argv: list[str]) -> int:
    if tuple(argv) not in {_RESTART, _ROLLBACK}:
        return 64
    completed = subprocess.run(  # noqa: S603
        (_SYSTEMCTL, "restart", "nginx"),
        check=False,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        cwd="/",
    )
    if completed.returncode == 0:
        return 0
    recovery = subprocess.run(  # noqa: S603
        (_SYSTEMCTL, "start", "nginx"),
        check=False,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        cwd="/",
    )
    return completed.returncode if recovery.returncode == 0 else 70


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
