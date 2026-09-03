from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected patch anchor not found in {path}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


# If the preceding finalizer did not commit, apply its deterministic patch first.
staged_v3 = ROOT / "scripts" / "apply_strict_review_v3.py"
if staged_v3.exists():
    runpy.run_path(str(staged_v3), run_name="__main__")

write(
    "src/eternal_polaris/memory.py",
    r'''from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Callable

from .models import Exchange


@dataclass(slots=True)
class _MemoryEntry:
    exchanges: deque[Exchange]
    touched_at: float


class ConversationMemory:
    def __init__(
        self,
        salt: str,
        max_exchanges: int = 3,
        ttl_seconds: int = 1800,
        max_users: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._salt = salt
        self._max_exchanges = max_exchanges
        self._ttl_seconds = ttl_seconds
        self._max_users = max_users
        self._clock = clock
        self._entries: dict[str, _MemoryEntry] = {}
        self._lock = threading.Lock()

    def key_for(self, user_id: str) -> str:
        return hashlib.sha256(f"{self._salt}:{user_id}".encode("utf-8")).hexdigest()

    def get(self, user_id: str) -> tuple[Exchange, ...]:
        key = self.key_for(user_id)
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                return ()
            entry.touched_at = now
            return tuple(entry.exchanges)

    def add(self, user_id: str, user_text: str, assistant_text: str) -> None:
        key = self.key_for(user_id)
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                if len(self._entries) >= self._max_users:
                    oldest_key = min(self._entries, key=lambda item: self._entries[item].touched_at)
                    self._entries.pop(oldest_key, None)
                entry = _MemoryEntry(deque(maxlen=self._max_exchanges), now)
                self._entries[key] = entry
            entry.exchanges.append(Exchange(user=user_text, assistant=assistant_text))
            entry.touched_at = now

    def _purge_expired(self, now: float) -> None:
        expired = [
            key for key, entry in self._entries.items() if now - entry.touched_at > self._ttl_seconds
        ]
        for key in expired:
            self._entries.pop(key, None)


class EventDeduplicator:
    """Thread-safe TTL idempotency window with a hard memory bound."""

    def __init__(
        self,
        ttl_seconds: int = 600,
        max_events: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_events = max_events
        self._clock = clock
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def first_seen(self, event_id: str) -> bool:
        if not event_id:
            return True
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            if event_id in self._seen:
                return False
            while len(self._seen) >= self._max_events:
                self._seen.popitem(last=False)
            self._seen[event_id] = now
            return True

    def forget(self, event_id: str) -> None:
        if not event_id:
            return
        with self._lock:
            self._seen.pop(event_id, None)

    def _purge_expired(self, now: float) -> None:
        while self._seen:
            _, oldest_timestamp = next(iter(self._seen.items()))
            if now - oldest_timestamp <= self._ttl_seconds:
                return
            self._seen.popitem(last=False)
''',
)

write(
    "src/eternal_polaris/config.py",
    r'''from __future__ import annotations

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
        chain_length + (total_capacity - chain_length) // worker_count
        for chain_length in range(1, max_chain + 1)
    )


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
    dedupe_max_events: int = 10_000
    webhook_worker_threads: int = 4
    webhook_queue_capacity: int = 0
    webhook_max_pending_per_key: int = 1
    direct_match_min_score: float = 0.46
    direct_match_min_margin: float = 0.08
    line_reply_max_attempts: int = 2
    line_reply_backoff_seconds: float = 0.25
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
        if self.memory_ttl_seconds < 1 or self.dedupe_ttl_seconds < 1:
            raise ConfigurationError("MEMORY_TTL_SECONDS 或 DEDUPE_TTL_SECONDS 超出允許範圍")
        if not 1 <= self.dedupe_max_events <= 1_000_000:
            raise ConfigurationError("DEDUPE_MAX_EVENTS 超出允許範圍")
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
        if (
            not 1 <= self.line_reply_max_attempts <= 5
            or not 0.0 <= self.line_reply_backoff_seconds <= 5.0
            or not 0.1 <= self.line_reply_timeout_seconds <= 15.0
        ):
            raise ConfigurationError(
                "LINE_REPLY_MAX_ATTEMPTS、LINE_REPLY_BACKOFF_SECONDS 或 LINE_REPLY_TIMEOUT_SECONDS 超出允許範圍"
            )

        retry_sleep_budget = self.line_reply_backoff_seconds * (
            2 ** (self.line_reply_max_attempts - 1) - 1
        )
        service_budget = (
            self.openai_timeout_seconds
            + self.line_reply_max_attempts * self.line_reply_timeout_seconds
            + retry_sleep_budget
        )
        serial_units = _worst_case_serial_units(
            self.webhook_worker_threads,
            self.webhook_queue_capacity,
            self.webhook_max_pending_per_key,
        )
        if serial_units * service_budget > _REPLY_TOKEN_BUDGET_SECONDS:
            raise ConfigurationError(
                "OPENAI_TIMEOUT_SECONDS、WEBHOOK_* 與 LINE_REPLY_* 的最壞延遲超出 reply token 安全預算"
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
                openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15")),
                app_port=int(os.getenv("APP_PORT", "5000")),
                knowledge_path=Path(os.getenv("KNOWLEDGE_PATH", "data/knowledge_cards.json")),
                memory_ttl_seconds=int(os.getenv("MEMORY_TTL_SECONDS", "1800")),
                dedupe_ttl_seconds=int(os.getenv("DEDUPE_TTL_SECONDS", "600")),
                dedupe_max_events=int(os.getenv("DEDUPE_MAX_EVENTS", "10000")),
                webhook_worker_threads=int(os.getenv("WEBHOOK_WORKER_THREADS", "4")),
                webhook_queue_capacity=int(os.getenv("WEBHOOK_QUEUE_CAPACITY", "0")),
                webhook_max_pending_per_key=int(os.getenv("WEBHOOK_MAX_PENDING_PER_KEY", "1")),
                direct_match_min_score=float(os.getenv("DIRECT_MATCH_MIN_SCORE", "0.46")),
                direct_match_min_margin=float(os.getenv("DIRECT_MATCH_MIN_MARGIN", "0.08")),
                line_reply_max_attempts=int(os.getenv("LINE_REPLY_MAX_ATTEMPTS", "2")),
                line_reply_backoff_seconds=float(os.getenv("LINE_REPLY_BACKOFF_SECONDS", "0.25")),
                line_reply_timeout_seconds=float(os.getenv("LINE_REPLY_TIMEOUT_SECONDS", "2")),
            )
        except ValueError as exc:
            raise ConfigurationError("數值型環境設定格式無效") from exc
''',
)

# The v3 app is the canonical base. Patch only the two privacy/capacity points.
replace_once("src/eternal_polaris/app.py", "import logging\nimport time", "import hashlib\nimport logging\nimport time")
replace_once(
    "src/eternal_polaris/app.py",
    "deduplicator = deduplicator or EventDeduplicator(settings.dedupe_ttl_seconds)",
    "deduplicator = deduplicator or EventDeduplicator(\n        settings.dedupe_ttl_seconds,\n        max_events=settings.dedupe_max_events,\n    )",
)
replace_once(
    "src/eternal_polaris/app.py",
    "key_fn=_event_processing_key,",
    "key_fn=partial(_event_processing_key, salt=settings.line_channel_secret),",
)
old_key_function = '''def _event_processing_key(event: Any) -> str:\n    source = getattr(event, "source", None)\n    source_type = _enum_value(getattr(source, "type", ""))\n    attribute = {\n        "user": "user_id",\n        "group": "group_id",\n        "room": "room_id",\n    }.get(source_type)\n    if attribute:\n        identifier = str(getattr(source, attribute, "") or "")\n        if identifier:\n            return f"{source_type}:{identifier}"\n    event_id = str(getattr(event, "webhook_event_id", "") or "")\n    return f"event:{event_id}" if event_id else ""\n'''
new_key_function = '''def _event_processing_key(event: Any, *, salt: str) -> str:\n    source = getattr(event, "source", None)\n    source_type = _enum_value(getattr(source, "type", ""))\n    attribute = {\n        "user": "user_id",\n        "group": "group_id",\n        "room": "room_id",\n    }.get(source_type)\n    identifier = str(getattr(source, attribute, "") or "") if attribute else ""\n    namespace = source_type or "event"\n    if not identifier:\n        identifier = str(getattr(event, "webhook_event_id", "") or "")\n    if not identifier:\n        return ""\n    digest = hashlib.sha256(f"{salt}:{namespace}:{identifier}".encode("utf-8")).hexdigest()\n    return f"{namespace}:{digest}"\n'''
replace_once("src/eternal_polaris/app.py", old_key_function, new_key_function)

write(
    "src/eternal_polaris/line_gateway.py",
    r'''from __future__ import annotations

import time
from typing import Callable, Protocol

from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage
from urllib3.exceptions import HTTPError as Urllib3HTTPError


class ReplyGateway(Protocol):
    def reply_text(self, reply_token: str, text: str) -> None: ...


SendFunction = Callable[[str, str], None]
SleepFunction = Callable[[float], None]


class LineReplyGateway:
    def __init__(
        self,
        access_token: str,
        *,
        max_attempts: int = 2,
        backoff_seconds: float = 0.25,
        request_timeout_seconds: float = 2.0,
        send: SendFunction | None = None,
        sleep: SleepFunction = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")
        self._configuration = Configuration(access_token=access_token)
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._send = send or self._send_once
        self._sleep = sleep

    def reply_text(self, reply_token: str, text: str) -> None:
        for attempt in range(self._max_attempts):
            try:
                self._send(reply_token, text)
                return
            except Exception as error:
                is_last_attempt = attempt + 1 >= self._max_attempts
                if is_last_attempt or not _is_retryable(error):
                    raise
                self._sleep(self._backoff_seconds * (2**attempt))

    def _send_once(self, reply_token: str, text: str) -> None:
        with ApiClient(self._configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)],
                ),
                _request_timeout=self._request_timeout_seconds,
            )


def _is_retryable(error: Exception) -> bool:
    status = getattr(error, "status", None)
    if status is not None:
        try:
            status_code = int(status)
        except (TypeError, ValueError):
            return False
        return status_code in {408, 429} or 500 <= status_code <= 599
    return isinstance(error, (TimeoutError, ConnectionError, OSError, Urllib3HTTPError))
''',
)

write(
    "tests/test_memory.py",
    r'''from __future__ import annotations

import pytest

from eternal_polaris.memory import ConversationMemory, EventDeduplicator


def test_memory_keeps_only_recent_exchanges_and_expires():
    now = [0.0]
    memory = ConversationMemory(
        "salt",
        max_exchanges=2,
        ttl_seconds=10,
        clock=lambda: now[0],
    )
    memory.add("U1", "q1", "a1")
    memory.add("U1", "q2", "a2")
    memory.add("U1", "q3", "a3")
    assert [item.user for item in memory.get("U1")] == ["q2", "q3"]
    now[0] = 11
    assert memory.get("U1") == ()


def test_memory_hash_key_does_not_expose_user_id():
    memory = ConversationMemory("salt")
    key = memory.key_for("U-secret")
    assert key != "U-secret"
    assert "U-secret" not in key
    assert len(key) == 64


def test_memory_evicts_oldest_user_at_capacity():
    now = [0.0]
    memory = ConversationMemory("salt", max_users=1, clock=lambda: now[0])
    memory.add("U1", "q1", "a1")
    now[0] = 1
    memory.add("U2", "q2", "a2")
    assert memory.get("U1") == ()
    assert memory.get("U2")[0].user == "q2"


def test_deduplicator_rejects_duplicates_then_expires():
    now = [0.0]
    dedupe = EventDeduplicator(ttl_seconds=10, clock=lambda: now[0])
    assert dedupe.first_seen("evt") is True
    assert dedupe.first_seen("evt") is False
    now[0] = 11
    assert dedupe.first_seen("evt") is True


def test_deduplicator_capacity_evicts_oldest_event():
    dedupe = EventDeduplicator(max_events=2)
    assert dedupe.first_seen("one")
    assert dedupe.first_seen("two")
    assert dedupe.first_seen("three")
    assert dedupe.first_seen("one") is True


def test_deduplicator_forget_allows_independent_retry():
    dedupe = EventDeduplicator()
    assert dedupe.first_seen("evt")
    dedupe.forget("evt")
    assert dedupe.first_seen("evt")
    assert dedupe.first_seen("")


def test_deduplicator_rejects_invalid_limits():
    with pytest.raises(ValueError):
        EventDeduplicator(ttl_seconds=0)
    with pytest.raises(ValueError):
        EventDeduplicator(max_events=0)
''',
)

# Small, idempotent test/config/document patches on top of v3.
replace_once(
    "tests/test_app.py",
    '''def test_event_processing_key_is_stable_per_conversation():\n    assert _event_processing_key(SimpleNamespace(source=SimpleNamespace(type="user", user_id="U1"))) == "user:U1"\n    assert _event_processing_key(SimpleNamespace(source=SimpleNamespace(type="group", group_id="G1"))) == "group:G1"\n    assert _event_processing_key(SimpleNamespace(source=None, webhook_event_id="evt")) == "event:evt"\n''',
    '''def test_event_processing_key_is_stable_and_hides_identifiers():\n    user = SimpleNamespace(source=SimpleNamespace(type="user", user_id="U1"))\n    same_user = SimpleNamespace(source=SimpleNamespace(type="user", user_id="U1"))\n    other_user = SimpleNamespace(source=SimpleNamespace(type="user", user_id="U2"))\n    key = _event_processing_key(user, salt="secret")\n    assert key == _event_processing_key(same_user, salt="secret")\n    assert key != _event_processing_key(other_user, salt="secret")\n    assert "U1" not in key\n    assert _event_processing_key(SimpleNamespace(source=None), salt="secret") == ""\n''',
)
replace_once(
    "tests/test_config.py",
    '"DEDUPE_TTL_SECONDS": "60",',
    '"DEDUPE_TTL_SECONDS": "60",\n        "DEDUPE_MAX_EVENTS": "5000",',
)
replace_once(
    "tests/test_config.py",
    "assert settings.dedupe_ttl_seconds == 60",
    "assert settings.dedupe_ttl_seconds == 60\n    assert settings.dedupe_max_events == 5000",
)
replace_once(
    "tests/test_line_gateway.py",
    "import pytest\n\nimport eternal_polaris.line_gateway as gateway_module",
    "import pytest\nfrom urllib3.exceptions import HTTPError as Urllib3HTTPError\n\nimport eternal_polaris.line_gateway as gateway_module",
)
replace_once(
    "tests/test_line_gateway.py",
    '''def test_programming_error_without_network_semantics_is_not_retried():''',
    '''def test_urllib3_transport_failure_is_retryable():\n    calls = []\n\n    def send(token, text):\n        calls.append((token, text))\n        if len(calls) == 1:\n            raise Urllib3HTTPError("temporary transport failure")\n\n    gateway = LineReplyGateway("token", max_attempts=2, backoff_seconds=0, send=send, sleep=lambda _: None)\n    gateway.reply_text("reply", "hello")\n    assert len(calls) == 2\n\n\ndef test_programming_error_without_network_semantics_is_not_retried():''',
)
replace_once(".env.example", "DEDUPE_TTL_SECONDS=600", "DEDUPE_TTL_SECONDS=600\nDEDUPE_MAX_EVENTS=10000")
replace_once(
    "README.md",
    "| `DEDUPE_TTL_SECONDS` | `600` | Webhook event ID 去重秒數 |",
    "| `DEDUPE_TTL_SECONDS` | `600` | Webhook event ID 去重秒數 |\n| `DEDUPE_MAX_EVENTS` | `10000` | 去重表硬上限，滿時淘汰最舊項目 |",
)
replace_once(
    "README.md",
    "使用者 ID 經雜湊後作為記憶索引",
    "使用者 ID 經雜湊後作為記憶與同對話 FIFO 索引",
)
replace_once(
    "docs/architecture.md",
    "| EventDeduplicator | 避免重複回答 | LINE redelivery | `webhookEventId` + TTL |",
    "| EventDeduplicator | 避免重複回答 | LINE redelivery、記憶體成長 | `webhookEventId` + TTL + 容量上限 |",
)
replace_once(
    "skills/line-bot-hardening/SKILL.md",
    "cap per-key backlog, and validate the worst-case queue + model + reply-retry time against the reply-token budget.",
    "cap per-key backlog, hash conversation keys kept in memory, bound the idempotency table, and validate the worst-case queue + model + reply-retry time against the reply-token budget.",
)

print("final strict hardening v4 applied")
