from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from backend.app.audit.service import redact

FIXED_COMMANDS: dict[str, tuple[str, ...]] = {
    "tasklist": ("tasklist.exe", "/FO", "CSV", "/NH"),
    "netstat_windows": ("netstat.exe", "-ano"),
    "ss": ("/usr/bin/ss", "-lntup"),
    "netstat_unix": ("/usr/bin/netstat", "-lntup"),
    "iostat": ("/usr/bin/iostat", "-x", "1", "1"),
    "lsof": ("/usr/bin/lsof", "--"),
    "journalctl": ("/usr/bin/journalctl", "--no-pager", "--output", "short-iso"),
    "systemctl": ("/usr/bin/systemctl", "show", "--no-pager"),
}


class ReadOnlyProvider:
    def __init__(
        self,
        allowed_roots: tuple[Path, ...] = (Path.cwd(),),
        allowed_services: tuple[str, ...] = ("nginx",),
    ) -> None:
        self.allowed_roots = tuple(path.resolve() for path in allowed_roots)
        self.allowed_services = frozenset(allowed_services)

    def capability_probe(self) -> dict[str, Any]:
        commands = ("ss", "netstat", "lsof", "iostat", "journalctl", "systemctl")
        return {
            "os": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "commands": {name: shutil.which(name) is not None for name in commands},
            "procfs": Path("/proc").is_dir(),
        }

    def system_snapshot(self) -> dict[str, Any]:
        disk = shutil.disk_usage(Path.cwd().anchor or ".")
        return {
            "captured_at": time.time(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
            "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        }

    def process_list(self, limit: int = 100) -> dict[str, Any]:
        if Path("/proc").is_dir():
            rows: list[dict[str, Any]] = []
            for item in sorted(Path("/proc").iterdir(), key=lambda path: path.name):
                if not item.name.isdigit() or len(rows) >= limit:
                    continue
                try:
                    name = (item / "comm").read_text(errors="replace").strip()
                    state = (item / "stat").read_text(errors="replace").split()[2]
                    rows.append({"pid": int(item.name), "name": name, "state": state})
                except (OSError, IndexError):
                    continue
            return {"processes": rows}
        output = self._run_fixed("tasklist", timeout=10, max_bytes=131072)
        return {"raw": output}

    def zombie_process_scan(self) -> dict[str, Any]:
        processes = self.process_list(limit=500).get("processes", [])
        return {"zombies": [item for item in processes if item.get("state") == "Z"]}

    def network_socket_list(self) -> dict[str, Any]:
        if platform.system() == "Windows":
            return {"raw": self._run_fixed("netstat_windows", 10, 131072)}
        key = "ss" if Path(FIXED_COMMANDS["ss"][0]).exists() else "netstat_unix"
        if not Path(FIXED_COMMANDS[key][0]).exists():
            raise RuntimeError("CAPABILITY_UNAVAILABLE: ss/netstat")
        return {"raw": self._run_fixed(key, 10, 131072)}

    def port_owner_lookup(self, port: int) -> dict[str, Any]:
        if not 1 <= port <= 65535:
            raise ValueError("port out of range")
        raw = self.network_socket_list()["raw"]
        lines = [line for line in str(raw).splitlines() if f":{port}" in line]
        return {"port": port, "matches": lines[:100]}

    def disk_usage_scan(self, path: str = ".") -> dict[str, Any]:
        target = self._safe_path(path)
        usage = shutil.disk_usage(target)
        return {"path": str(target), "total": usage.total, "used": usage.used, "free": usage.free}

    def large_file_scan(
        self, path: str = ".", min_bytes: int = 10_000_000, limit: int = 100
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        matches: list[dict[str, Any]] = []
        for root, dirs, files in os.walk(target, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
            for name in files:
                item = Path(root) / name
                try:
                    if item.is_symlink():
                        continue
                    size = item.stat().st_size
                except OSError:
                    continue
                if size >= min_bytes:
                    matches.append({"path": str(item), "size": size})
                    if len(matches) >= limit:
                        return {"files": matches, "truncated": True}
        return {"files": matches, "truncated": False}

    def open_file_lookup(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        executable = Path(FIXED_COMMANDS["lsof"][0])
        if not executable.exists():
            return {"path": str(target), "supported": False, "reason": "lsof unavailable"}
        output = self._run_argv((*FIXED_COMMANDS["lsof"], str(target)), 10, 131072)
        return {"path": str(target), "supported": True, "raw": output}

    def journal_query(self, unit: str | None = None, lines: int = 100) -> dict[str, Any]:
        if not 1 <= lines <= 1000:
            raise ValueError("line limit out of range")
        if unit is not None:
            self._validate_service(unit)
        executable = Path(FIXED_COMMANDS["journalctl"][0])
        if not executable.exists():
            return {
                "unit": unit,
                "lines": [],
                "supported": False,
                "reason": "journalctl unavailable",
            }
        argv = (*FIXED_COMMANDS["journalctl"], "-n", str(lines))
        if unit is not None:
            argv = (*argv, "-u", unit)
        output = self._run_argv(argv, 15, 262144)
        return {"unit": unit, "lines": output.splitlines()[:lines], "supported": True}

    def service_status(self, service: str) -> dict[str, Any]:
        self._validate_service(service)
        executable = Path(FIXED_COMMANDS["systemctl"][0])
        if not executable.exists():
            return {"service": service, "supported": False, "reason": "systemctl unavailable"}
        properties = "ActiveState,SubState,LoadState,Result,MainPID"
        output = self._run_argv(
            (*FIXED_COMMANDS["systemctl"], f"--property={properties}", service),
            10,
            65536,
        )
        parsed = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
        return {"service": service, "supported": True, "properties": parsed}

    def config_drift_check(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        return {"path": str(target), "status": "BASELINE_UNAVAILABLE"}

    def io_diagnose(self) -> dict[str, Any]:
        executable = Path(FIXED_COMMANDS["iostat"][0])
        if not executable.exists():
            return {"supported": False, "reason": "iostat unavailable"}
        return {"supported": True, "raw": self._run_fixed("iostat", 10, 131072)}

    def security_baseline_scan(self) -> dict[str, Any]:
        return {"checks": [{"id": "default_mode", "status": "PASS", "value": "READ_ONLY"}]}

    def _safe_path(self, value: str) -> Path:
        target = Path(value).resolve(strict=True)
        if target.is_symlink() or not any(
            target == root or root in target.parents for root in self.allowed_roots
        ):
            raise ValueError("PATH_REJECTED")
        return target

    @staticmethod
    def _run_fixed(key: str, timeout: int, max_bytes: int) -> str:
        argv = FIXED_COMMANDS[key]
        return ReadOnlyProvider._run_argv(argv, timeout, max_bytes)

    @staticmethod
    def _run_argv(argv: tuple[str, ...], timeout: int, max_bytes: int) -> str:
        if (
            not argv
            or not Path(argv[0]).is_absolute()
            and argv[0]
            not in {
                "tasklist.exe",
                "netstat.exe",
            }
        ):
            raise ValueError("EXECUTABLE_NOT_ALLOWED")
        # argv is selected only from the immutable FIXED_COMMANDS registry.
        completed = subprocess.run(  # noqa: S603
            argv, capture_output=True, timeout=timeout, check=False
        )
        output = completed.stdout[:max_bytes].decode(errors="replace")
        return redact_text(str(redact({"output": output})["output"]))

    def _validate_service(self, service: str) -> None:
        if service not in self.allowed_services:
            raise ValueError("SERVICE_NOT_ALLOWED")


class DemoProvider(ReadOnlyProvider):
    def capability_probe(self) -> dict[str, Any]:
        return {
            "os": "Kylin V11 DEMO",
            "architecture": "loongarch64-demo",
            "commands": {},
            "procfs": True,
        }

    def system_snapshot(self) -> dict[str, Any]:
        return {
            "captured_at": 1_783_748_644,
            "hostname": "demo-kylin",
            "platform": "Kylin V11 DEMO",
            "cpu_count": 8,
            "load_average": [0.8, 0.7, 0.6],
            "disk": {"total": 100_000, "used": 82_000, "free": 18_000},
        }

    def process_list(self, limit: int = 100) -> dict[str, Any]:
        return {
            "processes": [
                {"pid": 101, "name": "demo-worker", "state": "R"},
                {"pid": 202, "name": "demo-zombie", "state": "Z"},
            ][:limit]
        }


def redact_text(value: str) -> str:
    patterns = (
        (r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer ***REDACTED***"),
        (r"\bsk-[A-Za-z0-9]{12,}\b", "sk-***REDACTED***"),
        (
            r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+",
            r"\1=***REDACTED***",
        ),
    )
    result = value
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    return result
