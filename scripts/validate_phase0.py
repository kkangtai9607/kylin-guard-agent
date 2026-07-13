"""Validate Phase 0 documents and examples without implementing product logic."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    ".env.example",
    "docs/01-软件功能需求分析.md",
    "docs/02-软件功能设计.md",
    "docs/07-接口文档.md",
    "docs/08-安全设计说明.md",
    "docs/09-比赛评分点映射.md",
    "docs/10-演示脚本.md",
    "docs/architecture/总体架构.md",
    "docs/architecture/业务闭环.md",
    "docs/architecture/Agent状态机.md",
    "docs/architecture/威胁模型.md",
    "docs/architecture/MCP-Tool元数据规范.md",
    "docs/architecture/数据库ER设计.md",
    "docs/architecture/adr/0001-初始技术选型.md",
    "config/app.example.yaml",
    "config/policy.example.yaml",
    "config/tools.example.yaml",
    "config/demo.example.yaml",
    "scripts/security_scan.py",
    "PLANS.md",
    "CURRENT_STATUS.md",
)
REQUIRED_TERMS = (
    "LLM",
    "确定性",
    "人工审批",
    "备份",
    "验证",
    "回滚",
    "UNTRUSTED_DATA",
    "隐藏思维",
    "LoongArch",
    "DEMO",
    "READ_ONLY",
    "CONTROLLED_EXECUTION",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty: {relative}")


def check_markdown_links(errors: list[str]) -> None:
    for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            decoded = target.replace("%20", " ")
            if not (path.parent / decoded).resolve().exists():
                errors.append(f"broken link: {path.relative_to(ROOT)} -> {target}")


def check_required_terms(errors: list[str]) -> None:
    corpus = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]
    )
    for term in REQUIRED_TERMS:
        if term not in corpus:
            errors.append(f"required term absent: {term}")


def check_phase_status(errors: list[str]) -> None:
    plans = (ROOT / "PLANS.md").read_text(encoding="utf-8")
    status = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    if not re.search(r"\|\s*0\s*\|[^\n]*\|\s*COMPLETED\s*\|", plans):
        errors.append("PLANS.md does not mark Phase 0 COMPLETED")
    if "Phase 0" not in status or "COMPLETED" not in status:
        errors.append("CURRENT_STATUS.md does not record Phase 0 COMPLETED")


def check_examples(errors: list[str]) -> None:
    env_lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    for line in env_lines:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if (
            any(marker in key.upper() for marker in ("KEY", "TOKEN", "PASSWORD", "SECRET"))
            and value
        ):
            errors.append(f"secret placeholder must be empty: {key}")

    for path in (ROOT / "config").glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        if "\t" in text:
            errors.append(f"tab indentation is not allowed: {path.relative_to(ROOT)}")
        if not any(line.rstrip().endswith(":") for line in text.splitlines()):
            errors.append(f"configuration has no mapping structure: {path.relative_to(ROOT)}")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)
    check_markdown_links(errors)
    check_required_terms(errors)
    check_phase_status(errors)
    check_examples(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Phase 0 validation passed: {len(REQUIRED_FILES)} required files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
