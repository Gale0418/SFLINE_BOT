from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_SECRET_NAMES = (
    "OPENAI_API_KEY",
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
)


class ConfigurationError(RuntimeError):
    """安全的設定錯誤；訊息只包含欄位名稱，不包含值。"""


@dataclass(frozen=True, slots=True)
class Settings:
    openai_api_key: str
    line_channel_secret: str
    line_channel_access_token: str
    openai_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = 15.0
    app_port: int = 5000
    knowledge_path: Path = Path("data/knowledge_cards.json")
    memory_ttl_seconds: int = 1800
    dedupe_ttl_seconds: int = 600

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "Settings":
        load_dotenv(dotenv_path=env_file, override=False, interpolate=False)
        missing = [name for name in REQUIRED_SECRET_NAMES if not os.getenv(name, "").strip()]
        if missing:
            raise ConfigurationError("缺少必要設定：" + ", ".join(missing))

        try:
            timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15"))
            port = int(os.getenv("APP_PORT", "5000"))
        except ValueError as exc:
            raise ConfigurationError("APP_PORT 或 OPENAI_TIMEOUT_SECONDS 格式無效") from exc
        if timeout <= 0 or not 1 <= port <= 65535:
            raise ConfigurationError("APP_PORT 或 OPENAI_TIMEOUT_SECONDS 超出允許範圍")

        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"].strip(),
            line_channel_secret=os.environ["LINE_CHANNEL_SECRET"].strip(),
            line_channel_access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"].strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna",
            openai_timeout_seconds=timeout,
            app_port=port,
            knowledge_path=Path(os.getenv("KNOWLEDGE_PATH", "data/knowledge_cards.json")),
        )
