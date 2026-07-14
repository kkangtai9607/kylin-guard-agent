from pathlib import Path

from backend.app.core.config import AppConfig, user_home_scan_roots


def test_user_home_scan_is_disabled_by_default() -> None:
    config = AppConfig()
    assert not config.user_home_scan_enabled
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
