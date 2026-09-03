from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "scripts" / "apply_strict_review_v2.py"), run_name="__main__")


def replace_exact(relative_path: str, old: str, new: str) -> None:
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {relative_path}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def write(relative_path: str, content: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


# Correct the staged shell guard and preserve compatibility with the existing
# private .env, which may still explicitly contain OPENAI_TIMEOUT_SECONDS=15.
replace_exact(".github/workflows/ci.yml", "          if tracked=", "          tracked=")
replace_exact("src/eternal_polaris/config.py", "openai_timeout_seconds: float = 5.0", "openai_timeout_seconds: float = 15.0")
replace_exact("src/eternal_polaris/config.py", "webhook_queue_capacity: int = 4", "webhook_queue_capacity: int = 0")
replace_exact("src/eternal_polaris/config.py", "webhook_max_pending_per_key: int = 4", "webhook_max_pending_per_key: int = 1")
replace_exact("src/eternal_polaris/config.py", 'os.getenv("OPENAI_TIMEOUT_SECONDS", "5")', 'os.getenv("OPENAI_TIMEOUT_SECONDS", "15")')
replace_exact("src/eternal_polaris/config.py", 'os.getenv("WEBHOOK_QUEUE_CAPACITY", "4")', 'os.getenv("WEBHOOK_QUEUE_CAPACITY", "0")')
replace_exact("src/eternal_polaris/config.py", 'os.getenv("WEBHOOK_MAX_PENDING_PER_KEY", "4")', 'os.getenv("WEBHOOK_MAX_PENDING_PER_KEY", "1")')
replace_exact("src/eternal_polaris/answer_service.py", "timeout_seconds: float = 5.0", "timeout_seconds: float = 15.0")
replace_exact(".env.example", "OPENAI_TIMEOUT_SECONDS=5", "OPENAI_TIMEOUT_SECONDS=15")
replace_exact(".env.example", "WEBHOOK_QUEUE_CAPACITY=4", "WEBHOOK_QUEUE_CAPACITY=0")
replace_exact(".env.example", "WEBHOOK_MAX_PENDING_PER_KEY=4", "WEBHOOK_MAX_PENDING_PER_KEY=1")
replace_exact("README.md", "| `OPENAI_TIMEOUT_SECONDS` | `5` |", "| `OPENAI_TIMEOUT_SECONDS` | `15` |")
replace_exact("README.md", "| `WEBHOOK_QUEUE_CAPACITY` | `4` |", "| `WEBHOOK_QUEUE_CAPACITY` | `0` |")
replace_exact("README.md", "| `WEBHOOK_MAX_PENDING_PER_KEY` | `4` |", "| `WEBHOOK_MAX_PENDING_PER_KEY` | `1` |")
replace_exact("tests/test_config.py", "assert settings.openai_timeout_seconds == 5", "assert settings.openai_timeout_seconds == 15")
replace_exact("tests/test_config.py", "assert _worst_case_serial_units(4, 4, 4) == 5", "assert _worst_case_serial_units(4, 0, 1) == 2")

write(
    "tests/test_app.py",
    r'''from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from types import SimpleNamespace

from eternal_polaris.answer_service import SERVICE_ERROR_REPLY
from eternal_polaris.app import (
    EMPTY_QUESTION_REPLY,
    QUESTION_TOO_LONG_REPLY,
    UNSUPPORTED_REPLY,
    _event_processing_key,
    create_app,
)
from eternal_polaris.dispatcher import InlineEventDispatcher
from eternal_polaris.models import BotAnswer, ScienceLabel


class FakeAnswerProvider:
    def __init__(self, answer=None, error=None):
        self.result = answer
        self.error = error
        self.calls = 0

    def answer(self, question, history):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class BlockingAnswerProvider(FakeAnswerProvider):
    def __init__(self, answer):
        super().__init__(answer)
        self.started = threading.Event()
        self.release = threading.Event()

    def answer(self, question, history):
        self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=2)
        return self.result


class SequencedAnswerProvider:
    def __init__(self, answer):
        self.answer_value = answer
        self.first_started = threading.Event()
        self.release_first = threading.Event()
        self.questions = []
        self.histories = []

    def answer(self, question, history):
        self.questions.append(question)
        self.histories.append(history)
        if question == "第一題":
            self.first_started.set()
            assert self.release_first.wait(timeout=2)
        return self.answer_value


class FakeReplyGateway:
    def __init__(self):
        self.replies = []
        self.sent = threading.Event()
        self._condition = threading.Condition()

    def reply_text(self, reply_token, text):
        with self._condition:
            self.replies.append((reply_token, text))
            self.sent.set()
            self._condition.notify_all()

    def wait_for_count(self, count, timeout=2):
        deadline = time.monotonic() + timeout
        with self._condition:
            while len(self.replies) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True


class FlakyReplyGateway(FakeReplyGateway):
    def __init__(self):
        super().__init__()
        self.attempts = 0

    def reply_text(self, reply_token, text):
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("simulated LINE failure")
        super().reply_text(reply_token, text)


class RejectingDispatcher:
    def submit_many(self, events, handler):
        return False

    def shutdown(self, *, wait=True):
        del wait


def _body(
    message_type="text",
    event_id="evt-1",
    source_type="user",
    text="黑洞真的存在嗎？",
    mode="active",
    reply_token="reply-1",
):
    message = {"id": f"m-{event_id}", "type": message_type, "quoteToken": f"quote-{event_id}"}
    if message_type == "text":
        message["text"] = text
    elif message_type == "image":
        message["contentProvider"] = {"type": "line"}
    source = {"type": source_type, "userId": "U-test"}
    if source_type == "group":
        source["groupId"] = "G-test"
    payload = {
        "destination": "U-bot",
        "events": [
            {
                "type": "message",
                "mode": mode,
                "timestamp": 1700000000000,
                "source": source,
                "webhookEventId": event_id,
                "deliveryContext": {"isRedelivery": False},
                "replyToken": reply_token,
                "message": message,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _signature(body, secret):
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _post(app, body, secret):
    return app.test_client().post(
        "/callback",
        data=body,
        headers={"X-Line-Signature": _signature(body, secret)},
    )


def _inline_app(settings, knowledge, provider=None, gateway=None, dispatcher=None):
    return create_app(
        settings,
        answer_provider=provider or FakeAnswerProvider(),
        reply_gateway=gateway or FakeReplyGateway(),
        knowledge=knowledge,
        dispatcher=dispatcher or InlineEventDispatcher(),
    )


def test_health_does_not_expose_config(settings, knowledge):
    app = _inline_app(settings, knowledge)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_missing_and_invalid_signatures_are_rejected(settings, knowledge):
    app = _inline_app(settings, knowledge)
    assert app.test_client().post("/callback", data=_body()).status_code == 400
    response = app.test_client().post("/callback", data=_body(), headers={"X-Line-Signature": "bad"})
    assert response.status_code == 400


def test_parse_error_is_rejected(settings, knowledge):
    app = _inline_app(settings, knowledge)
    body = "not-json"
    assert _post(app, body, settings.line_channel_secret).status_code == 400


def test_empty_events_return_200(settings, knowledge):
    body = '{"destination":"U-bot","events":[]}'
    app = _inline_app(settings, knowledge)
    assert _post(app, body, settings.line_channel_secret).status_code == 200


def test_verified_webhook_acknowledges_before_slow_answer_finishes(settings, knowledge):
    card = knowledge.by_id["ov001"]
    provider = BlockingAnswerProvider(BotAnswer(card.label, "回答。", (card.id,)))
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    dispatcher = app.extensions["event_dispatcher"]
    body = _body()
    try:
        started = time.monotonic()
        response = _post(app, body, settings.line_channel_secret)
        elapsed = time.monotonic() - started
        assert response.status_code == 200
        assert elapsed < 1.0
        assert provider.started.wait(timeout=1)
        assert gateway.replies == []
        provider.release.set()
        assert gateway.sent.wait(timeout=1)
    finally:
        provider.release.set()
        dispatcher.shutdown(wait=True)


def test_same_user_messages_are_fifo_and_second_sees_first_history(settings, knowledge):
    card = knowledge.by_id["ov001"]
    provider = SequencedAnswerProvider(BotAnswer(card.label, "回答。", (card.id,)))
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    dispatcher = app.extensions["event_dispatcher"]
    try:
        first = _body(event_id="fifo-1", text="第一題", reply_token="reply-1")
        second = _body(event_id="fifo-2", text="第二題", reply_token="reply-2")
        assert _post(app, first, settings.line_channel_secret).status_code == 200
        assert provider.first_started.wait(timeout=1)
        assert _post(app, second, settings.line_channel_secret).status_code == 200
        time.sleep(0.05)
        assert provider.questions == ["第一題"]
        provider.release_first.set()
        assert gateway.wait_for_count(2)
    finally:
        provider.release_first.set()
        dispatcher.shutdown(wait=True)
    assert provider.questions == ["第一題", "第二題"]
    assert provider.histories[0] == ()
    assert provider.histories[1][-1].user == "第一題"
    assert [token for token, _ in gateway.replies] == ["reply-1", "reply-2"]


def test_queue_full_returns_503_instead_of_silently_dropping(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway, dispatcher=RejectingDispatcher())
    response = _post(app, _body(), settings.line_channel_secret)
    assert response.status_code == 503
    assert provider.calls == 0
    assert gateway.replies == []


def test_standby_event_is_acknowledged_without_reply(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway)
    response = _post(app, _body(mode="standby"), settings.line_channel_secret)
    assert response.status_code == 200
    assert provider.calls == 0
    assert gateway.replies == []


def test_text_event_replies_once_and_duplicate_is_ignored(settings, knowledge):
    card = knowledge.by_id["ov001"]
    provider = FakeAnswerProvider(BotAnswer(card.label, "黑洞已有多種觀測證據。", (card.id,)))
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway)
    body = _body()
    assert _post(app, body, settings.line_channel_secret).status_code == 200
    assert _post(app, body, settings.line_channel_secret).status_code == 200
    assert provider.calls == 1
    assert len(gateway.replies) == 1
    assert "【已觀測／已驗證】" in gateway.replies[0][1]


def test_non_text_and_group_events_get_fixed_reply(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway)
    assert _post(app, _body(message_type="image"), settings.line_channel_secret).status_code == 200
    assert _post(app, _body(source_type="group", event_id="group-1"), settings.line_channel_secret).status_code == 200
    assert provider.calls == 0
    assert gateway.replies == [("reply-1", UNSUPPORTED_REPLY), ("reply-1", UNSUPPORTED_REPLY)]


def test_blank_and_long_questions_are_rejected_without_model_call(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway)
    assert _post(app, _body(text="   "), settings.line_channel_secret).status_code == 200
    assert _post(app, _body(text="星" * 1001, event_id="long-1"), settings.line_channel_secret).status_code == 200
    assert provider.calls == 0
    assert gateway.replies == [
        ("reply-1", EMPTY_QUESTION_REPLY),
        ("reply-1", QUESTION_TOO_LONG_REPLY),
    ]


def test_openai_failure_gets_safe_fallback(settings, knowledge):
    gateway = FakeReplyGateway()
    app = _inline_app(settings, knowledge, FakeAnswerProvider(error=TimeoutError()), gateway)
    _post(app, _body(), settings.line_channel_secret)
    assert gateway.replies == [("reply-1", SERVICE_ERROR_REPLY)]


def test_reply_failure_clears_dedupe_for_independently_arriving_duplicate(settings, knowledge):
    card = knowledge.by_id["ov001"]
    provider = FakeAnswerProvider(BotAnswer(card.label, "回答。", (card.id,)))
    gateway = FlakyReplyGateway()
    app = _inline_app(settings, knowledge, provider, gateway)
    body = _body()
    headers = {"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    client = app.test_client()
    assert client.post("/callback", data=body, headers=headers).status_code == 500
    assert gateway.attempts == 1
    assert client.post("/callback", data=body, headers=headers).status_code == 200
    assert gateway.attempts == 2
    assert len(gateway.replies) == 1


def test_event_processing_key_is_stable_per_conversation():
    assert _event_processing_key(SimpleNamespace(source=SimpleNamespace(type="user", user_id="U1"))) == "user:U1"
    assert _event_processing_key(SimpleNamespace(source=SimpleNamespace(type="group", group_id="G1"))) == "group:G1"
    assert _event_processing_key(SimpleNamespace(source=None, webhook_event_id="evt")) == "event:evt"
''',
)

# Add route disclosure and tighten the wording around post-ACK failures.
replace_exact(
    "README.md",
    "- 以 `webhookEventId` 在記憶體內去重 10 分鐘。",
    "- 以 `webhookEventId` 在記憶體內去重 10 分鐘；背景 reply 最終失敗後只會清除本機去重鍵，LINE 並不保證因這種 post-ACK 失敗再次投遞。",
)
replace_exact(
    "README.md",
    "| `WEBHOOK_QUEUE_CAPACITY` | `0` | 等待中事件上限，不含執行中的工作 |",
    "| `WEBHOOK_QUEUE_CAPACITY` | `0` | 全域額外等待容量；預設過載直接 503 |",
)
replace_exact(
    "README.md",
    "| `WEBHOOK_MAX_PENDING_PER_KEY` | `1` | 同一對話最多等待事件數 |",
    "| `WEBHOOK_MAX_PENDING_PER_KEY` | `1` | 每個對話鍵在執行事件後最多再等 1 件 |",
)
replace_exact(
    "docs/report-outline.md",
    "- `eval_questions.csv`：30 題基準覆蓋。",
    "- `eval_questions.csv`：30 題基準覆蓋；production-hybrid 報表需揭露 local/model route distribution。\n- 另以 `--model-only` 隔離模型能力，禁止把 deterministic fast-path 分數冒充模型分數。",
)

print("strict-review v3 files applied")
