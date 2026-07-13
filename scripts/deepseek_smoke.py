from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.llm.provider import (  # noqa: E402
    OpenAICompatibleProvider,
    provider_from_environment,
)


class SmokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^ok$")
    message_zh: str = Field(min_length=1, max_length=50)


def main() -> int:
    os.environ.setdefault("LLM_PROVIDER", "deepseek")
    os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-v4-pro")
    provider = provider_from_environment()
    if not isinstance(provider, OpenAICompatibleProvider):
        print("DeepSeek 未配置：请仅通过 DEEPSEEK_API_KEY 环境变量注入新 Key。")
        return 2
    result = provider.generate_structured(
        prompt='请返回 JSON：status 固定为 "ok"，message_zh 用中文说明在线连接正常。',
        schema=SmokeResponse,
    )
    print(f"DeepSeek 在线结构化调用通过：{result.status} / {result.message_zh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
