from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_SECRET_NAMES = (
    "OPENAI_API_KEY",
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
)
_REPLY_TOKEN_BUDGET_SECONDS = 55.0


class ConfigurationError(RuntimeError):
    """安全的設定錯誤；訊息只包含欄位名稱，不包含值。"""


def _worst_case_serial_units(
    worker_count: int,
    queue_capacity: int,
    max_pending_per_key: int,
) -> int:
    total_capacity = worker_count + queue_capacity
    max_chain = min(max_pending_per_key + 1, total_capacity)
    return max(
        chain + math.ceil(max(0, total_capacity - chain) / worker_count)
        for chain in range(1, max_chain + 1)
    )


@dataclass(frozen=True, slots=True)
class Settings:
    openai_api_key: str
    line_channel_secret: str
    line_channel_access_token: str
    openai_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = 5.0
    app_port: int = 5000
    knowledge_path: Path = Path("data/knowledge_cards.json")
    quiz_path: Path = Path("data/quiz_questions.tsv")
    memory_ttl_seconds: int = 1800
    dedupe_ttl_seconds: int = 600
    quiz_ttl_seconds: int = 1800
    webhook_worker_threads: int = 4
    webhook_queue_capacity: int = 4
    webhook_max_pending_per_key: int = 4
    direct_match_min_score: float = 0.46
    direct_match_min_margin: float = 0.08
    line_reply_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not all(
            (
                self.openai_api_key.strip(),
                self.line_channel_secret.strip(),
                self.line_channel_access_token.strip(),
            )
        ):
            raise ConfigurationError("必要金鑰不可空白")
        if self.openai_timeout_seconds <= 0 or not 1 <= self.app_port <= 65535:
            raise ConfigurationError("APP_PORT 或 OPENAI_TIMEOUT_SECONDS 超出允許範圍")
        if min(self.memory_ttl_seconds, self.dedupe_ttl_seconds, self.quiz_ttl_seconds) < 1:
            raise ConfigurationError("MEMORY_TTL_SECONDS、DEDUPE_TTL_SECONDS 或 QUIZ_TTL_SECONDS 超出允許範圍")
        if (
            not 1 <= self.webhook_worker_threads <= 32
            or not 0 <= self.webhook_queue_capacity <= 10_000
            or not 0 <= self.webhook_max_pending_per_key <= 100
        ):
            raise ConfigurationError(
                "WEBHOOK_WORKER_THREADS、WEBHOOK_QUEUE_CAPACITY 或 WEBHOOK_MAX_PENDING_PER_KEY 超出允許範圍"
            )
        if not 0.0 <= self.direct_match_min_score <= 1.0 or not 0.0 <= self.direct_match_min_margin <= 1.0:
            raise ConfigurationError("DIRECT_MATCH_MIN_SCORE 或 DIRECT_MATCH_MIN_MARGIN 超出允許範圍")
        if not 0.1 <= self.line_reply_timeout_seconds <= 15.0:
            raise ConfigurationError("LINE_REPLY_TIMEOUT_SECONDS 超出允許範圍")

        service_budget = self.openai_timeout_seconds + self.line_reply_timeout_seconds
        serial_units = _worst_case_serial_units(
            self.webhook_worker_threads,
            self.webhook_queue_capacity,
            self.webhook_max_pending_per_key,
        )
        if serial_units * service_budget > _REPLY_TOKEN_BUDGET_SECONDS:
            raise ConfigurationError(
                "OPENAI_TIMEOUT_SECONDS、WEBHOOK_* 與 LINE_REPLY_TIMEOUT_SECONDS 的最壞延遲超出 reply token 安全預算"
            )

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "Settings":
        load_dotenv(dotenv_path=env_file, override=False, interpolate=False)
        missing = [name for name in REQUIRED_SECRET_NAMES if not os.getenv(name, "").strip()]
        if missing:
            raise ConfigurationError("缺少必要設定：" + ", ".join(missing))
        try:
            return cls(
                openai_api_key=os.environ["OPENAI_API_KEY"].strip(),
                line_channel_secret=os.environ["LINE_CHANNEL_SECRET"].strip(),
                line_channel_access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"].strip(),
                openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna",
                openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "5")),
                app_port=int(os.getenv("APP_PORT", "5000")),
                knowledge_path=Path(os.getenv("KNOWLEDGE_PATH", "data/knowledge_cards.json")),
                quiz_path=Path(os.getenv("QUIZ_PATH", "data/quiz_questions.tsv")),
                memory_ttl_seconds=int(os.getenv("MEMORY_TTL_SECONDS", "1800")),
                dedupe_ttl_seconds=int(os.getenv("DEDUPE_TTL_SECONDS", "600")),
                quiz_ttl_seconds=int(os.getenv("QUIZ_TTL_SECONDS", "1800")),
                webhook_worker_threads=int(os.getenv("WEBHOOK_WORKER_THREADS", "4")),
                webhook_queue_capacity=int(os.getenv("WEBHOOK_QUEUE_CAPACITY", "4")),
                webhook_max_pending_per_key=int(os.getenv("WEBHOOK_MAX_PENDING_PER_KEY", "4")),
                direct_match_min_score=float(os.getenv("DIRECT_MATCH_MIN_SCORE", "0.46")),
                direct_match_min_margin=float(os.getenv("DIRECT_MATCH_MIN_MARGIN", "0.08")),
                line_reply_timeout_seconds=float(os.getenv("LINE_REPLY_TIMEOUT_SECONDS", "2")),
            )
        except ValueError as exc:
            raise ConfigurationError("數值型環境設定格式無效") from exc
