from collections.abc import Iterator
from pathlib import Path

import pytest

from backend.app.core.config import AppConfig, load_config, parse_path_list, user_home_scan_roots


def test_user_home_scan_is_enabled_by_default_without_scanning_whole_home() -> None:
    config = AppConfig()
    assert config.user_home_scan_enabled
    assert all("/home/" not in str(path) for path in config.read_only_scan_roots())
    assert all("/home/" not in str(path) for path in config.controlled_cleanup_roots())


def test_user_home_scan_expands_only_low_risk_existing_subdirs(tmp_path: Path) -> None:
    home = tmp_path / "home"
    alice = home / "alice"
    bob = home / "bob"
    for path in (
        alice / ".cache",
        alice / "Downloads",
        alice / ".ssh",
        bob / "tmp",
    ):
        path.mkdir(parents=True)

    roots = user_home_scan_roots(
        enabled=True,
        subdirs=(".cache", "Downloads", "tmp", "../escape"),
        home_root=home,
    )

    assert set(roots) == {alice / ".cache", alice / "Downloads", bob / "tmp"}
    assert alice / ".ssh" not in roots


def test_user_home_scan_fails_closed_when_home_cannot_be_listed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()

    def fake_is_dir(self: Path) -> bool:
        return True if self == home else Path.exists(self)

    monkeypatch.setattr(Path, "is_dir", fake_is_dir)

    def denied(self: Path) -> Iterator[Path]:
        if self == home:
            raise PermissionError("denied")
        return iter(())

    monkeypatch.setattr(Path, "iterdir", denied)

    roots = user_home_scan_roots(
        enabled=True,
        subdirs=(".cache", "Downloads", "tmp"),
        home_root=home,
    )

    assert roots == ()


def test_user_home_scan_uses_explicit_login_home_when_home_listing_is_denied(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    vmuser = home / "vmuser"
    for path in (vmuser / ".cache", vmuser / "Downloads", vmuser / ".ssh"):
        path.mkdir(parents=True)

    original_iterdir = Path.iterdir

    def denied(self: Path) -> Iterator[Path]:
        if self == home:
            raise PermissionError("denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", denied)

    roots = user_home_scan_roots(
        enabled=True,
        subdirs=(".cache", "Downloads", "tmp"),
        home_root=home,
        explicit_paths=(vmuser,),
    )

    assert set(roots) == {vmuser / ".cache", vmuser / "Downloads"}
    assert vmuser / ".ssh" not in roots


def test_user_home_scan_accepts_explicit_low_risk_subdir_paths(tmp_path: Path) -> None:
    vmuser = tmp_path / "home" / "vmuser"
    cache = vmuser / ".cache"
    downloads = vmuser / "Downloads"
    for path in (cache, downloads):
        path.mkdir(parents=True)

    roots = user_home_scan_roots(
        enabled=True,
        subdirs=(".cache", "Downloads", "tmp"),
        home_root=tmp_path / "blocked-home",
        explicit_paths=(cache, downloads),
    )

    assert roots == (cache, downloads)


def test_app_config_includes_explicit_home_paths_in_scan_and_cleanup_roots(tmp_path: Path) -> None:
    vmuser = tmp_path / "home" / "vmuser"
    cache = vmuser / ".cache"
    cache.mkdir(parents=True)

    config = AppConfig(user_home_scan_paths=(vmuser,))

    assert cache in config.read_only_scan_roots()
    assert cache in config.controlled_cleanup_roots()


def test_parse_path_list_uses_comma_and_semicolon_separators() -> None:
    assert parse_path_list("/home/vmuser;/home/admin, /home/demo") == (
        Path("/home/vmuser"),
        Path("/home/admin"),
        Path("/home/demo"),
    )


def test_load_config_applies_user_home_scan_paths_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KYLIN_GUARD_USER_HOME_SCAN_PATHS", "/home/vmuser/.cache,/home/vmuser/Downloads")

    config = load_config(path=tmp_path / "missing.yaml")

    assert config.user_home_scan_paths == (Path("/home/vmuser/.cache"), Path("/home/vmuser/Downloads"))
