"""Minimal repository safety scan for Phase 0 and later incremental extension."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "dist",
    "node_modules",
    "site-packages",
    "claude-code-system-prompts",
}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".vue", ".sh", ".ps1"}
TEXT_SUFFIXES = SOURCE_SUFFIXES | {".md", ".yaml", ".yml", ".toml", ".json", ".env", ".example"}

# Patterns are assembled to keep the scanner from reporting its own definitions.
DANGEROUS_SOURCE_PATTERNS = {
    "shell enabled": re.compile(r"shell\s*=\s*" + "True"),
    "dynamic evaluation": re.compile(r"\b" + "ev" + r"al\s*\("),
    "dynamic execution": re.compile(r"\b" + "ex" + r"ec\s*\("),
    "generic shell tool": re.compile(r"\b" + "run" + r"_shell\b"),
    "generic command tool": re.compile(r"\b" + "execute" + r"_command\b"),
    "generic script tool": re.compile(r"\b" + "run" + r"_script\b"),
}
CONFIG_SECRET_VALUE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)[ \t]*[:=][ \t]*[\"']?([^\s\"']+)"
)
SOURCE_SECRET_VALUE = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)[ \t]*=[ \t]*"
    r"[\"']([^\"']+)[\"']"
)
PROVIDER_KEY = re.compile(r"\b" + "sk-" + r"[A-Za-z0-9]{20,}\b")
PLACEHOLDER_VALUES = {"", "null", "none", "changeme", "example", "${value}"}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env.example" or path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def scan_source(path: Path, text: str, findings: list[str]) -> None:
    if path.suffix.lower() not in SOURCE_SUFFIXES or path.name == Path(__file__).name:
        return
    for label, pattern in DANGEROUS_SOURCE_PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{path.relative_to(ROOT)}:{line}: {label}")


def scan_secrets(path: Path, text: str, findings: list[str]) -> None:
    for match in PROVIDER_KEY.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        findings.append(f"{path.relative_to(ROOT)}:{line}: provider key-like value")

    suffix = path.suffix.lower()
    if suffix in SOURCE_SUFFIXES:
        pattern = SOURCE_SECRET_VALUE
    elif suffix in {".yaml", ".yml", ".toml", ".json", ".env", ".example"}:
        pattern = CONFIG_SECRET_VALUE
    else:
        return
    for match in pattern.finditer(text):
        value = match.group(2).strip().strip("\"'").lower()
        if value in PLACEHOLDER_VALUES or value.startswith("${") or value.endswith("_env"):
            continue
        if path.name == ".env.example" and value == "read_only":
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(f"{path.relative_to(ROOT)}:{line}: possible hard-coded secret")


def main() -> int:
    findings: list[str] = []
    files = iter_files()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scan_source(path, text, findings)
        scan_secrets(path, text, findings)

    if findings:
        for finding in findings:
            print(f"SECURITY: {finding}")
        return 1
    print(f"Security scan passed: {len(files)} text/source files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
