from collections.abc import Iterator
from pathlib import Path

import pytest

from backend.app.core.config import AppConfig, user_home_scan_roots


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
