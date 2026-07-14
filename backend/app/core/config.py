from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = "sqlite:///./data/kylin_guard.db"
    busy_timeout_ms: int = Field(default=5000, ge=100, le=60000)


class ManagedConfigTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    path: Path
    validator: Literal["nginx"]
    validator_path: Path


class ManagedProcessTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    process_name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.@-]+$")
    service: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.@-]+$")


class ControlledExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_cleanup_roots: tuple[Path, ...] = (
        Path("/var/log/kylin-guard-managed"),
        Path("/var/log"),
        Path("/tmp"),  # noqa: S108 - intentional controlled cleanup scan root.
        Path("/var/tmp"),  # noqa: S108 - intentional controlled cleanup scan root.
    )
    protected_paths: tuple[Path, ...] = (
        Path("/etc"),
        Path("/root"),
        Path("/boot"),
        Path("/proc"),
        Path("/sys"),
        Path("/dev"),
        Path("/run"),
        Path("/var/lib"),
    )
    backup_root: Path = Path("/var/lib/kylin-guard/backups")
    minimum_age_days: int = Field(default=7, ge=1, le=3650)
    minimum_size_bytes: int = Field(default=10_000_000, ge=1)
    allowed_services: tuple[str, ...] = ("nginx",)
    systemctl_path: Path = Path("/usr/bin/systemctl")
    executor_socket_path: Path = Path("/run/kylin-guard/executor.sock")
    managed_configs: tuple[ManagedConfigTarget, ...] = (
        ManagedConfigTarget(
            target_id="nginx-main",
            path=Path("/etc/nginx/nginx.conf"),
            validator="nginx",
            validator_path=Path("/usr/sbin/nginx"),
        ),
    )
    managed_processes: tuple[ManagedProcessTarget, ...] = (
        ManagedProcessTarget(process_name="nginx", service="nginx"),
    )


def user_home_scan_roots(
    *, enabled: bool, subdirs: tuple[str, ...], home_root: Path = Path("/home")
) -> tuple[Path, ...]:
    if not enabled or not home_root.is_dir():
        return ()
    roots: list[Path] = []
    for user_dir in home_root.iterdir():
        try:
            if not user_dir.is_dir() or user_dir.is_symlink():
                continue
            for subdir in subdirs:
                if subdir.startswith("/") or ".." in Path(subdir).parts:
                    continue
                target = user_dir / subdir
                if target.is_dir() and not target.is_symlink():
                    roots.append(target)
        except OSError:
            continue
    return tuple(roots)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "KylinGuard Agent"
    mode: Literal["DEMO", "READ_ONLY", "CONTROLLED_EXECUTION"] = "READ_ONLY"
    database: DatabaseConfig = DatabaseConfig()
    snapshot_scheduler_enabled: bool = False
    snapshot_interval_seconds: int = Field(default=300, ge=30, le=86400)
    user_home_scan_enabled: bool = False
    user_home_scan_subdirs: tuple[str, ...] = (".cache", "Downloads", "tmp")
    controlled_execution: ControlledExecutionConfig = ControlledExecutionConfig()

    def read_only_scan_roots(self) -> tuple[Path, ...]:
        return (
            Path.cwd(),
            Path("/var/log"),
            Path("/tmp"),  # noqa: S108 - intentional read-only cleanup scan root.
            Path("/var/tmp"),  # noqa: S108 - intentional read-only cleanup scan root.
            *user_home_scan_roots(
                enabled=self.user_home_scan_enabled,
                subdirs=self.user_home_scan_subdirs,
            ),
        )

    def controlled_cleanup_roots(self) -> tuple[Path, ...]:
        return (
            *self.controlled_execution.allowed_cleanup_roots,
            *user_home_scan_roots(
                enabled=self.user_home_scan_enabled,
                subdirs=self.user_home_scan_subdirs,
            ),
        )


class EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KYLIN_GUARD_", extra="ignore")
    config_file: Path = Path("config/runtime.yaml")
    database_url: str | None = None
    mode: Literal["DEMO", "READ_ONLY", "CONTROLLED_EXECUTION"] | None = None
    snapshot_scheduler_enabled: bool | None = None
    snapshot_interval_seconds: int | None = None
    user_home_scan_enabled: bool | None = None


def load_config(path: Path | None = None) -> AppConfig:
    env = EnvironmentSettings()
    source = path or env.config_file
    raw: dict[str, Any] = {}
    if source.is_file():
        loaded = yaml.safe_load(source.read_text(encoding="utf-8"))
        if loaded is not None and not isinstance(loaded, dict):
            raise ValueError("configuration root must be a mapping")
        raw = loaded or {}
    app_raw = raw.get("app", raw)
    config = AppConfig.model_validate(app_raw)
    overrides: dict[str, Any] = {}
    if env.mode is not None:
        overrides["mode"] = env.mode
    if env.database_url is not None:
        overrides["database"] = config.database.model_copy(update={"url": env.database_url})
    if env.snapshot_scheduler_enabled is not None:
        overrides["snapshot_scheduler_enabled"] = env.snapshot_scheduler_enabled
    if env.snapshot_interval_seconds is not None:
        overrides["snapshot_interval_seconds"] = env.snapshot_interval_seconds
    if env.user_home_scan_enabled is not None:
        overrides["user_home_scan_enabled"] = env.user_home_scan_enabled
    return config.model_copy(update=overrides)


@lru_cache
def get_config() -> AppConfig:
    return load_config()
