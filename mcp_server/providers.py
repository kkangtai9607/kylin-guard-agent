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
    "ip_addr": ("/usr/sbin/ip", "-details", "addr", "show"),
    "ip_route": ("/usr/sbin/ip", "route", "show"),
    "lsof": ("/usr/bin/lsof", "--"),
    "journalctl": ("/usr/bin/journalctl", "--no-pager", "--output", "short-iso"),
    "journalctl_kernel": ("/usr/bin/journalctl", "--no-pager", "--output", "short-iso", "-k"),
    "systemctl": ("/usr/bin/systemctl", "show", "--no-pager"),
    "systemctl_timers": ("/usr/bin/systemctl", "list-timers", "--all", "--no-pager", "--plain", "--no-legend"),
    "rpm_query": ("/usr/bin/rpm", "-qa", "--qf", "%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n"),
    "last": ("/usr/bin/last", "-n"),
}


def _default_allowed_roots() -> tuple[Path, ...]:
    candidates = (
        Path("/"),
        Path.cwd(),
        Path("/var/log"),
        Path("/tmp"),  # noqa: S108 - intentional read-only cleanup scan root.
        Path("/var/tmp"),  # noqa: S108 - intentional read-only cleanup scan root.
    )
    roots: list[Path] = []
    for path in candidates:
        try:
            if path.exists() and path.is_dir():
                roots.append(path)
        except OSError:
            continue
    return tuple(roots or (Path.cwd(),))


def _default_cleanup_roots() -> tuple[Path, ...]:
    candidates = (
        Path.cwd(),
        Path("/var/log"),
        Path("/tmp"),  # noqa: S108 - intentional controlled cleanup candidate scan root.
        Path("/var/tmp"),  # noqa: S108 - intentional controlled cleanup candidate scan root.
    )
    roots: list[Path] = []
    for path in candidates:
        try:
            if path.exists() and path.is_dir():
                roots.append(path)
        except OSError:
            continue
    return tuple(roots or (Path.cwd(),))


def _is_filesystem_root(path: Path) -> bool:
    return path.parent == path


class ReadOnlyProvider:
    def __init__(
        self,
        allowed_roots: tuple[Path, ...] | None = None,
        cleanup_roots: tuple[Path, ...] | None = None,
        protected_roots: tuple[Path, ...] | None = None,
        allowed_services: tuple[str, ...] = ("nginx", "sshd"),
    ) -> None:
        self.allowed_roots = tuple(path.resolve() for path in (allowed_roots or _default_allowed_roots()))
        cleanup_candidates = cleanup_roots if cleanup_roots is not None else _default_cleanup_roots()
        self.cleanup_roots = tuple(
            path.resolve()
            for path in cleanup_candidates
            if path.exists() and path.is_dir() and not _is_filesystem_root(path.resolve())
        )
        self.protected_roots = tuple(
            path.resolve()
            for path in (
                protected_roots
                or (
                    Path("/etc/shadow"),
                    Path("/etc/gshadow"),
                    Path("/root"),
                    Path("/boot"),
                    Path("/proc"),
                    Path("/sys"),
                    Path("/dev"),
                    Path("/run"),
                    Path("/var/lib"),
                )
            )
            if path.exists()
        )
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
        filesystems = []
        for root in self.allowed_roots:
            try:
                usage = shutil.disk_usage(root)
                filesystems.append(
                    {
                        "path": str(root),
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                    }
                )
            except OSError:
                continue
        return {
            "captured_at": time.time(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
            "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
            "filesystems": filesystems,
        }

    def memory_snapshot(self) -> dict[str, Any]:
        meminfo = Path("/proc/meminfo")
        if not meminfo.is_file():
            return {"supported": False, "reason": "procfs meminfo unavailable"}
        values: dict[str, int] = {}
        for line in self._read_limited_lines(meminfo, limit=200):
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            match = re.search(r"\d+", raw_value)
            if match:
                values[key] = int(match.group(0)) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        used = max(total - available, 0) if total else 0
        return {
            "supported": True,
            "total": total,
            "available": available,
            "used": used,
            "swap_total": values.get("SwapTotal", 0),
            "swap_free": values.get("SwapFree", 0),
            "raw_keys": {key: values[key] for key in sorted(values)[:80]},
        }

    def process_list(self, limit: int = 100) -> dict[str, Any]:
        if Path("/proc").is_dir():
            rows: list[dict[str, Any]] = []
            for item in sorted(Path("/proc").iterdir(), key=lambda path: path.name):
                if not item.name.isdigit():
                    continue
                try:
                    name = (item / "comm").read_text(errors="replace").strip()
                    stat_text = (item / "stat").read_text(errors="replace")
                    right = stat_text.rsplit(")", 1)[1].strip().split()
                    state = right[0]
                    cpu_ticks = int(right[11]) + int(right[12]) if len(right) > 12 else 0
                    rss_pages = int(right[21]) if len(right) > 21 else 0
                    rows.append(
                        {
                            "pid": int(item.name),
                            "name": name,
                            "state": state,
                            "cpu_ticks": cpu_ticks,
                            "rss_pages": rss_pages,
                        }
                    )
                except (OSError, IndexError, ValueError):
                    continue
            rows.sort(key=lambda row: int(row.get("cpu_ticks", 0)), reverse=True)
            return {"processes": rows[:limit], "sort": "cpu_ticks_desc"}
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
        filesystems: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root in self.allowed_roots:
            try:
                resolved = str(root.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                root_usage = shutil.disk_usage(root)
                filesystems.append(
                    {
                        "path": str(root),
                        "total": root_usage.total,
                        "used": root_usage.used,
                        "free": root_usage.free,
                    }
                )
            except OSError:
                continue
        return {
            "path": str(target),
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "filesystems": filesystems,
        }

    def filesystem_inventory(self) -> dict[str, Any]:
        mounts: list[dict[str, Any]] = []
        mounts_file = Path("/proc/mounts")
        if mounts_file.is_file():
            for line in self._read_limited_lines(mounts_file, limit=300):
                parts = line.split()
                if len(parts) < 4:
                    continue
                device, mount_point, fs_type, options = parts[:4]
                if any(mount_point.startswith(prefix) for prefix in ("/proc", "/sys", "/dev")):
                    continue
                item: dict[str, Any] = {
                    "device": device,
                    "mount_point": mount_point,
                    "fs_type": fs_type,
                    "options": options[:300],
                }
                try:
                    usage = shutil.disk_usage(mount_point)
                    item.update({"total": usage.total, "used": usage.used, "free": usage.free})
                    if hasattr(os, "statvfs"):
                        stats = os.statvfs(mount_point)
                        item.update(
                            {
                                "files": stats.f_files,
                                "files_free": stats.f_ffree,
                                "files_used": max(stats.f_files - stats.f_ffree, 0),
                            }
                        )
                except OSError:
                    item["usage_supported"] = False
                mounts.append(item)
        else:
            for root in self.allowed_roots:
                try:
                    usage = shutil.disk_usage(root)
                    mounts.append({"mount_point": str(root), "total": usage.total, "used": usage.used, "free": usage.free})
                except OSError:
                    continue
        return {"supported": bool(mounts), "mounts": mounts[:100]}

    def large_file_scan(
        self, path: str = ".", min_bytes: int = 10_000_000, limit: int = 100
    ) -> dict[str, Any]:
        if path == "__cleanup_roots__":
            matches: list[dict[str, Any]] = []
            scanned_roots: list[str] = []
            truncated = False
            for target in self.cleanup_roots:
                if not target.exists() or not target.is_dir():
                    continue
                scanned_roots.append(str(target))
                root_result = self._large_file_scan_one(target, min_bytes, max(1, limit - len(matches)))
                matches.extend(root_result["files"])
                truncated = truncated or root_result["truncated"]
                if len(matches) >= limit:
                    truncated = True
                    break
            return {
                "path": path,
                "scanned_roots": scanned_roots,
                "files": matches[:limit],
                "truncated": truncated,
            }
        target = self._safe_path(path)
        return self._large_file_scan_one(target, min_bytes, limit)

    def _large_file_scan_one(
        self, target: Path, min_bytes: int, limit: int
    ) -> dict[str, Any]:
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
            return self._proc_open_file_lookup(target)
        output = self._run_argv((*FIXED_COMMANDS["lsof"], str(target)), 10, 131072)
        return {"path": str(target), "supported": True, "raw": output}

    def _proc_open_file_lookup(self, target: Path) -> dict[str, Any]:
        """Best-effort Linux fallback when lsof is absent.

        This is read-only and deterministic: it walks /proc/*/fd symlinks and
        reports matching PIDs. Permission-denied entries are skipped and exposed
        as a warning count instead of making the whole tool fail.
        """
        proc = Path("/proc")
        if not proc.is_dir():
            return {"path": str(target), "supported": False, "reason": "procfs unavailable"}
        try:
            target_stat = target.stat()
        except OSError:
            return {"path": str(target), "supported": False, "reason": "target stat failed"}
        matches: list[str] = []
        denied = 0
        for pid_dir in proc.iterdir():
            if not pid_dir.name.isdigit():
                continue
            fd_dir = pid_dir / "fd"
            try:
                fd_entries = tuple(fd_dir.iterdir())
            except OSError:
                denied += 1
                continue
            for fd in fd_entries:
                try:
                    fd_stat = fd.stat()
                except OSError:
                    continue
                if fd_stat.st_ino == target_stat.st_ino and fd_stat.st_dev == target_stat.st_dev:
                    comm = ""
                    try:
                        comm = (pid_dir / "comm").read_text(encoding="utf-8", errors="replace").strip()
                    except OSError:
                        comm = "unknown"
                    matches.append(f"pid={pid_dir.name} comm={redact(comm)} fd={fd.name}")
                    break
        return {
            "path": str(target),
            "supported": True,
            "method": "procfs_fd",
            "raw": "\n".join(matches),
            "warnings": [f"proc_fd_permission_denied={denied}"] if denied else [],
        }

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

    def network_config_snapshot(self) -> dict[str, Any]:
        route_executable = Path(FIXED_COMMANDS["ip_route"][0])
        resolv = Path("/etc/resolv.conf")
        dns_lines = self._read_limited_lines(resolv, limit=50) if resolv.is_file() else []
        if not route_executable.exists():
            return {
                "supported": False,
                "reason": "ip command unavailable",
                "dns": [redact_text(line) for line in dns_lines],
            }
        return {
            "supported": True,
            "routes": self._run_fixed("ip_route", 10, 131072).splitlines()[:200],
            "addresses": self._run_fixed("ip_addr", 10, 131072).splitlines()[:300],
            "dns": [redact_text(line) for line in dns_lines],
        }

    def package_inventory(self, limit: int = 200) -> dict[str, Any]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit out of range")
        executable = Path(FIXED_COMMANDS["rpm_query"][0])
        if not executable.exists():
            return {"supported": False, "reason": "rpm unavailable", "packages": []}
        rows = self._run_fixed("rpm_query", 20, 524288).splitlines()
        return {"supported": True, "packages": rows[:limit], "total_visible": len(rows)}

    def scheduled_task_inventory(self) -> dict[str, Any]:
        crontab = Path("/etc/crontab")
        cron_d = Path("/etc/cron.d")
        result: dict[str, Any] = {
            "crontab": [redact_text(line) for line in self._read_limited_lines(crontab, limit=120)] if crontab.is_file() else [],
            "cron_d_files": [],
            "timers_supported": False,
            "timers": [],
        }
        if cron_d.is_dir():
            try:
                result["cron_d_files"] = [
                    item.name for item in sorted(cron_d.iterdir(), key=lambda path: path.name)[:100]
                    if item.is_file() and not item.is_symlink()
                ]
            except OSError:
                result["cron_d_files"] = []
        executable = Path(FIXED_COMMANDS["systemctl_timers"][0])
        if executable.exists():
            result["timers_supported"] = True
            result["timers"] = self._run_fixed("systemctl_timers", 10, 131072).splitlines()[:100]
        return result

    def login_audit(self, limit: int = 30) -> dict[str, Any]:
        if not 1 <= limit <= 200:
            raise ValueError("limit out of range")
        executable = Path(FIXED_COMMANDS["last"][0])
        if not executable.exists():
            return {"supported": False, "reason": "last unavailable", "records": []}
        output = self._run_argv((*FIXED_COMMANDS["last"], str(limit)), 10, 131072)
        return {"supported": True, "records": output.splitlines()[:limit]}

    def kernel_log_query(self, lines: int = 80) -> dict[str, Any]:
        if not 1 <= lines <= 500:
            raise ValueError("line limit out of range")
        executable = Path(FIXED_COMMANDS["journalctl_kernel"][0])
        if not executable.exists():
            return {"supported": False, "reason": "journalctl unavailable", "lines": []}
        argv = (*FIXED_COMMANDS["journalctl_kernel"], "-p", "warning", "-n", str(lines))
        output = self._run_argv(argv, 15, 262144)
        return {"supported": True, "lines": output.splitlines()[:lines]}

    def security_baseline_scan(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = [
            {"id": "fixed_tool_registry", "status": "PASS", "value": "no generic shell tool"},
            {
                "id": "procfs_available",
                "status": "PASS" if Path("/proc").is_dir() else "SKIPPED",
                "value": str(Path("/proc").is_dir()),
            },
            {
                "id": "systemctl_available",
                "status": "PASS" if Path(FIXED_COMMANDS["systemctl"][0]).exists() else "SKIPPED",
                "value": FIXED_COMMANDS["systemctl"][0],
            },
            {
                "id": "journalctl_available",
                "status": "PASS" if Path(FIXED_COMMANDS["journalctl"][0]).exists() else "SKIPPED",
                "value": FIXED_COMMANDS["journalctl"][0],
            },
        ]
        checks.extend(self._service_baseline_checks())
        checks.extend(self._network_baseline_checks())
        checks.extend(self._zombie_baseline_checks())
        return {"checks": checks}

    def _service_baseline_checks(self) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for service in sorted(self.allowed_services):
            try:
                status = self.service_status(service)
                properties = status.get("properties")
                active = str(properties.get("ActiveState", "unknown")) if isinstance(properties, dict) else "unsupported"
                checks.append(
                    {
                        "id": f"service_{service}",
                        "status": "PASS" if active == "active" else "WARN",
                        "value": active,
                    }
                )
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
                checks.append({"id": f"service_{service}", "status": "SKIPPED", "value": "unavailable"})
        return checks

    def _network_baseline_checks(self) -> list[dict[str, Any]]:
        try:
            raw = str(self.network_socket_list().get("raw", ""))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            return [{"id": "listening_ports", "status": "SKIPPED", "value": "ss/netstat unavailable"}]
        suspicious = []
        for line in raw.splitlines():
            lowered = line.lower()
            if any(token in lowered for token in ("0.0.0.0:", "[::]:", "*:")):
                suspicious.append(line[:300])
        return [
            {
                "id": "listening_ports",
                "status": "WARN" if suspicious else "PASS",
                "value": suspicious[:10],
            }
        ]

    def _zombie_baseline_checks(self) -> list[dict[str, Any]]:
        try:
            zombies = self.zombie_process_scan().get("zombies", [])
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            return [{"id": "zombie_processes", "status": "SKIPPED", "value": "procfs unavailable"}]
        return [
            {
                "id": "zombie_processes",
                "status": "WARN" if zombies else "PASS",
                "value": len(zombies) if isinstance(zombies, list) else 0,
            }
        ]

    def _safe_path(self, value: str) -> Path:
        target = Path(value).resolve(strict=True)
        if target.is_symlink() or not any(
            target == root or root in target.parents for root in self.allowed_roots
        ):
            raise ValueError("PATH_REJECTED")
        if any(target == root or root in target.parents for root in self.protected_roots):
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

    @staticmethod
    def _read_limited_lines(path: Path, *, limit: int) -> list[str]:
        lines: list[str] = []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for _, line in zip(range(limit), handle, strict=False):
                    cleaned = redact_text(line.rstrip("\n\r"))
                    lines.append(cleaned[:1000])
        except OSError:
            return []
        return lines


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

    def memory_snapshot(self) -> dict[str, Any]:
        return {"supported": True, "total": 16_000_000_000, "available": 9_000_000_000, "used": 7_000_000_000, "swap_total": 4_000_000_000, "swap_free": 3_500_000_000, "raw_keys": {}}

    def filesystem_inventory(self) -> dict[str, Any]:
        return {"supported": True, "mounts": [{"device": "/dev/demo-root", "mount_point": "/", "fs_type": "ext4", "total": 100_000, "used": 82_000, "free": 18_000}]}

    def network_config_snapshot(self) -> dict[str, Any]:
        return {"supported": True, "routes": ["default via 192.0.2.1 dev eth0"], "addresses": ["eth0 inet 192.0.2.10/24"], "dns": ["nameserver 192.0.2.53"]}

    def package_inventory(self, limit: int = 200) -> dict[str, Any]:
        return {"supported": True, "packages": ["kernel 6.6-demo loongarch64", "nginx 1.24-demo loongarch64"][:limit], "total_visible": 2}

    def scheduled_task_inventory(self) -> dict[str, Any]:
        return {"crontab": [], "cron_d_files": ["demo-maintenance"], "timers_supported": True, "timers": ["demo.timer loaded active waiting"]}

    def login_audit(self, limit: int = 30) -> dict[str, Any]:
        return {"supported": True, "records": ["admin pts/0 192.0.2.20 Tue Jul 14 10:00 still logged in"][:limit]}

    def kernel_log_query(self, lines: int = 80) -> dict[str, Any]:
        return {"supported": True, "lines": ["demo-kernel: no recent warning"][:lines]}


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
