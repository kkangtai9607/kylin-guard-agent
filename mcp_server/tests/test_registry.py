import subprocess
from pathlib import Path

import pytest

import mcp_server.providers as providers
from mcp_server.providers import DemoProvider, ReadOnlyProvider, redact_text
from mcp_server.registry import ToolRegistry


def test_registry_contains_only_read_only_tools() -> None:
    tools = ToolRegistry.for_mode("READ_ONLY").list_tools()
    assert len(tools) == 21
    assert all(tool.read_only for tool in tools)
    assert {tool.name for tool in tools} >= {
        "system_snapshot",
        "process_list",
        "service_status",
        "memory_snapshot",
        "filesystem_inventory",
        "network_config_snapshot",
        "package_inventory",
        "scheduled_task_inventory",
        "login_audit",
        "kernel_log_query",
    }


def test_demo_provider_is_repeatable_and_labeled() -> None:
    registry = ToolRegistry(DemoProvider(), is_demo=True)
    first = registry.call("system_snapshot")
    second = registry.call("system_snapshot")
    assert first.data == second.data
    assert first.is_demo and first.trust_label == "UNTRUSTED_DATA"


def test_unknown_tool_is_rejected() -> None:
    result = ToolRegistry.for_mode("READ_ONLY").call("run_anything")
    assert result.status == "FAILED"
    assert result.error_code == "TOOL_NOT_REGISTERED"


def test_allowed_root_and_large_file_limit(tmp_path: Path) -> None:
    (tmp_path / "large.log").write_bytes(b"x" * 64)
    provider = ReadOnlyProvider((tmp_path,))
    result = provider.large_file_scan(str(tmp_path), min_bytes=1, limit=1)
    assert result["truncated"] is True
    assert len(result["files"]) == 1


def test_cleanup_roots_are_separate_from_global_read_roots(tmp_path: Path) -> None:
    cleanup = tmp_path / "cleanup"
    other = tmp_path / "other"
    cleanup.mkdir()
    other.mkdir()
    (cleanup / "candidate.log").write_bytes(b"x" * 64)
    (other / "ignored.log").write_bytes(b"x" * 64)

    provider = ReadOnlyProvider(allowed_roots=(tmp_path,), cleanup_roots=(cleanup,))
    result = provider.large_file_scan("__cleanup_roots__", min_bytes=1, limit=10)

    assert result["scanned_roots"] == [str(cleanup.resolve())]
    assert [item["path"] for item in result["files"]] == [str(cleanup / "candidate.log")]


def test_path_outside_allowed_root_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    provider = ReadOnlyProvider((allowed,))
    with pytest.raises(ValueError, match="PATH_REJECTED"):
        provider.disk_usage_scan(str(outside))


def test_symlink_escape_is_not_scanned(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    (outside / "secret.log").write_bytes(b"x" * 64)
    link = allowed / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    provider = ReadOnlyProvider((allowed,))
    result = provider.large_file_scan(str(allowed), min_bytes=1)
    assert result["files"] == []


def test_open_file_lookup_falls_back_to_procfs_without_lsof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not Path("/proc").is_dir():
        pytest.skip("procfs fallback is Linux-only")
    target = tmp_path / "Downloads" / "installer.msi"
    target.parent.mkdir()
    target.write_bytes(b"x" * 16)
    monkeypatch.setitem(providers.FIXED_COMMANDS, "lsof", (str(tmp_path / "missing-lsof"), "--"))

    result = ReadOnlyProvider(allowed_roots=(tmp_path,)).open_file_lookup(str(target))

    assert result["supported"] is True
    assert result["method"] == "procfs_fd"
    assert "raw" in result


def test_parameter_validation_and_missing_capability() -> None:
    provider = ReadOnlyProvider()
    with pytest.raises(ValueError, match="port out of range"):
        provider.port_owner_lookup(70000)
    result = provider.io_diagnose()
    assert "supported" in result
    assert "supported" in provider.memory_snapshot()
    assert "mounts" in provider.filesystem_inventory()
    assert "dns" in provider.network_config_snapshot()


def test_new_inventory_tools_are_bounded_and_read_only() -> None:
    provider = ReadOnlyProvider()
    assert "packages" in provider.package_inventory(limit=5)
    assert "timers" in provider.scheduled_task_inventory()
    assert "records" in provider.login_audit(limit=5)
    assert "lines" in provider.kernel_log_query(lines=5)
    with pytest.raises(ValueError, match="limit out of range"):
        provider.package_inventory(limit=0)
    with pytest.raises(ValueError, match="line limit"):
        provider.kernel_log_query(lines=1000)


def test_service_and_journal_parameters_are_constrained() -> None:
    default_provider = ReadOnlyProvider()
    result = default_provider.service_status("sshd")
    assert result["service"] == "sshd"
    assert result["supported"] is False or "properties" in result

    provider = ReadOnlyProvider(allowed_services=("nginx",))
    with pytest.raises(ValueError, match="SERVICE_NOT_ALLOWED"):
        provider.service_status("sshd")
    with pytest.raises(ValueError, match="SERVICE_NOT_ALLOWED"):
        provider.journal_query("../../shadow")
    with pytest.raises(ValueError, match="line limit"):
        provider.journal_query(lines=1001)


def test_untrusted_text_is_redacted() -> None:
    value = "Authorization: Bearer abc.def api_key=value sk-abcdefghijklmnop"
    cleaned = redact_text(value)
    assert "abc.def" not in cleaned
    assert "api_key=value" not in cleaned
    assert "abcdefghijklmnop" not in cleaned


def test_fixed_command_timeout_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired("fixed", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        ReadOnlyProvider._run_fixed("tasklist", 1, 1024)
