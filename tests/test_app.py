from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random

from eternal_polaris.answer_service import SERVICE_ERROR_REPLY
from eternal_polaris.app import QUESTION_TOO_LONG_REPLY, UNSUPPORTED_REPLY, create_app
from eternal_polaris.dispatcher import InlineEventDispatcher
from eternal_polaris.models import BotAnswer, ScienceLabel
from eternal_polaris.quiz import QuizManager


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


class FakeReplyGateway:
    def __init__(self):
        self.replies = []

    def reply_text(self, reply_token, text, quick_replies=()):
        self.replies.append((reply_token, text, tuple(quick_replies)))


class RejectingDispatcher:
    def submit_many(self, events, handler):
        del events, handler
        return False

    def shutdown(self, *, wait=True):
        del wait


def _body(message_type="text", event_id="evt-1", source_type="user", text="黑洞真的存在嗎？"):
    message = {"id": "m-1", "type": message_type, "quoteToken": "quote-1"}
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
                "mode": "active",
                "timestamp": 1700000000000,
                "source": source,
                "webhookEventId": event_id,
                "deliveryContext": {"isRedelivery": False},
                "replyToken": "reply-1",
                "message": message,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _signature(body, secret):
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _make_app(settings, knowledge, quiz_bank, provider=None, gateway=None, dispatcher=None, manager=None):
    return create_app(
        settings,
        answer_provider=provider or FakeAnswerProvider(),
        reply_gateway=gateway or FakeReplyGateway(),
        knowledge=knowledge,
        quiz_bank=quiz_bank,
        quiz_manager=manager,
        dispatcher=dispatcher or InlineEventDispatcher(),
    )


def _post(app, body, settings):
    return app.test_client().post(
        "/callback",
        data=body,
        headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)},
    )


def test_health_reports_valid_quiz_bank(settings, knowledge, quiz_bank):
    app = _make_app(settings, knowledge, quiz_bank)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "quiz_questions": 96}


def test_invalid_signature_is_rejected(settings, knowledge, quiz_bank):
    app = _make_app(settings, knowledge, quiz_bank)
    response = app.test_client().post("/callback", data=_body(), headers={"X-Line-Signature": "bad"})
    assert response.status_code == 400


def test_empty_events_return_200(settings, knowledge, quiz_bank):
    body = '{"destination":"U-bot","events":[]}'
    app = _make_app(settings, knowledge, quiz_bank)
    assert _post(app, body, settings).status_code == 200


def test_worker_capacity_rejection_returns_503(settings, knowledge, quiz_bank):
    app = _make_app(settings, knowledge, quiz_bank, dispatcher=RejectingDispatcher())
    response = _post(app, _body(), settings)
    assert response.status_code == 503
    assert response.get_data(as_text=True) == "Busy"


def test_text_event_replies_once_and_duplicate_is_ignored(settings, knowledge, quiz_bank):
    card = knowledge.cards[0]
    provider = FakeAnswerProvider(BotAnswer(card.label, "黑洞已有多種觀測證據。", (card.id,)))
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    body = _body()
    assert _post(app, body, settings).status_code == 200
    assert _post(app, body, settings).status_code == 200
    assert provider.calls == 1
    assert len(gateway.replies) == 1
    assert "【已觀測／已驗證】" in gateway.replies[0][1]


def test_help_is_deterministic_and_skips_model(settings, knowledge, quiz_bank):
    provider = FakeAnswerProvider(error=AssertionError("model must not run"))
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    assert _post(app, _body(text="你會什麼？"), settings).status_code == 200
    assert provider.calls == 0
    assert "接受星之試煉" in gateway.replies[0][1]
    assert len(gateway.replies[0][2]) == 3


def test_challenge_command_opens_vault_menu(settings, knowledge, quiz_bank):
    provider = FakeAnswerProvider(error=AssertionError("model must not run"))
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    _post(app, _body(text="出題"), settings)
    assert "寶庫不拒絕求知之人" in gateway.replies[0][1]
    assert len(gateway.replies[0][2]) == 6


def test_active_quiz_accepts_typed_letter(settings, knowledge, quiz_bank):
    manager = QuizManager(
        quiz_bank,
        salt=settings.line_channel_secret,
        random_source=random.Random(7),
    )
    manager.start("U-test", vault="cosmos", difficulty="easy")
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, gateway=gateway, manager=manager)
    _post(app, _body(text="A"), settings)
    assert "解說：" in gateway.replies[0][1]
    assert "下一道星門" in gateway.replies[0][1]


def test_non_text_event_gets_fixed_reply(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, gateway=gateway)
    _post(app, _body(message_type="image"), settings)
    assert gateway.replies[0][1] == UNSUPPORTED_REPLY


def test_openai_failure_gets_safe_fallback(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    app = _make_app(
        settings,
        knowledge,
        quiz_bank,
        provider=FakeAnswerProvider(error=TimeoutError()),
        gateway=gateway,
    )
    _post(app, _body(), settings)
    assert gateway.replies[0][1] == SERVICE_ERROR_REPLY


def test_long_question_is_rejected_without_openai_call(settings, knowledge, quiz_bank):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    _post(app, _body(text="星" * 1001), settings)
    assert provider.calls == 0
    assert gateway.replies[0][1] == QUESTION_TOO_LONG_REPLY
