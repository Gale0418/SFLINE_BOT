from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_SECRET_NAMES = (
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
)
_AI_PROVIDERS = {"auto", "google", "openai"}
_GOOGLE_MODEL_PREFIXES = ("gemma-", "gemini-")
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


def _is_google_model(model: str) -> bool:
    return model.startswith(_GOOGLE_MODEL_PREFIXES)


@dataclass(frozen=True, slots=True)
class Settings:
    # ``openai_api_key`` / ``openai_model`` remain the active-key/model fields for
    # backwards compatibility with the existing app wiring. When Google is
    # selected, __post_init__ rewrites them to GEMINI_API_KEY / GEMINI_MODEL.
    openai_api_key: str
    line_channel_secret: str
    line_channel_access_token: str
    ai_provider: str = "openai"
    gemini_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    gemini_model: str = "gemma-4-31b-it"
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
        provider = self.ai_provider.strip().lower()
        if provider not in _AI_PROVIDERS:
            raise ConfigurationError("AI_PROVIDER 必須是 auto、google 或 openai")

        if not self.line_channel_secret.strip() or not self.line_channel_access_token.strip():
            raise ConfigurationError("LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN 不可空白")

        if provider == "auto":
            provider = "google" if self.gemini_api_key.strip() else "openai"

        if provider == "google":
            google_key = self.gemini_api_key.strip()
            if not google_key:
                raise ConfigurationError("AI_PROVIDER=google 需要 GEMINI_API_KEY")
            google_model = self.gemini_model.strip() or "gemma-4-31b-it"
            if not _is_google_model(google_model):
                raise ConfigurationError("GEMINI_MODEL 必須是 gemma-* 或 gemini-* 模型 ID")
            object.__setattr__(self, "ai_provider", "google")
            object.__setattr__(self, "openai_api_key", google_key)
            object.__setattr__(self, "openai_model", google_model)
        else:
            if not self.openai_api_key.strip():
                raise ConfigurationError("AI_PROVIDER=openai 需要 OPENAI_API_KEY")
            openai_model = self.openai_model.strip() or "gpt-5.6-luna"
            if _is_google_model(openai_model):
                raise ConfigurationError("OPENAI_MODEL 不可使用 gemma-* 或 gemini-* 模型 ID")
            object.__setattr__(self, "ai_provider", "openai")
            object.__setattr__(self, "openai_model", openai_model)

        if self.openai_timeout_seconds <= 0 or not 1 <= self.app_port <= 65535:
            raise ConfigurationError("APP_PORT 或 MODEL_TIMEOUT_SECONDS 超出允許範圍")
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
                "MODEL_TIMEOUT_SECONDS、WEBHOOK_* 與 LINE_REPLY_TIMEOUT_SECONDS 的最壞延遲超出 reply token 安全預算"
            )

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "Settings":
        load_dotenv(dotenv_path=env_file, override=False, interpolate=False)

        missing = [name for name in REQUIRED_SECRET_NAMES if not os.getenv(name, "").strip()]
        if missing:
            raise ConfigurationError("缺少必要設定：" + ", ".join(missing))

        provider = os.getenv("AI_PROVIDER", "auto").strip().lower() or "auto"
        if provider not in _AI_PROVIDERS:
            raise ConfigurationError("AI_PROVIDER 必須是 auto、google 或 openai")

        gemini_key = (
            os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
        )
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if provider == "auto" and not gemini_key and not openai_key:
            raise ConfigurationError("缺少 AI 金鑰：請設定 GEMINI_API_KEY 或 OPENAI_API_KEY")
        if provider == "google" and not gemini_key:
            raise ConfigurationError("AI_PROVIDER=google 需要 GEMINI_API_KEY")
        if provider == "openai" and not openai_key:
            raise ConfigurationError("AI_PROVIDER=openai 需要 OPENAI_API_KEY")

        try:
            return cls(
                openai_api_key=openai_key,
                line_channel_secret=os.environ["LINE_CHANNEL_SECRET"].strip(),
                line_channel_access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"].strip(),
                ai_provider=provider,
                gemini_api_key=gemini_key,
                openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna",
                gemini_model=os.getenv("GEMINI_MODEL", "gemma-4-31b-it").strip() or "gemma-4-31b-it",
                openai_timeout_seconds=float(
                    os.getenv(
                        "MODEL_TIMEOUT_SECONDS",
                        os.getenv("OPENAI_TIMEOUT_SECONDS", "5"),
                    )
                ),
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
