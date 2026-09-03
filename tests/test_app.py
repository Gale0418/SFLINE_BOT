from __future__ import annotations

import base64
import hashlib
import hmac
import json

from eternal_polaris.answer_service import SERVICE_ERROR_REPLY
from eternal_polaris.app import QUESTION_TOO_LONG_REPLY, UNSUPPORTED_REPLY, create_app
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


class FakeReplyGateway:
    def __init__(self):
        self.replies = []

    def reply_text(self, reply_token, text):
        self.replies.append((reply_token, text))


class FlakyReplyGateway(FakeReplyGateway):
    def __init__(self):
        super().__init__()
        self.attempts = 0

    def reply_text(self, reply_token, text):
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("simulated LINE failure")
        super().reply_text(reply_token, text)


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


def test_health_does_not_expose_config(settings, knowledge):
    answer = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=answer, reply_gateway=gateway, knowledge=knowledge)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_invalid_signature_is_rejected(settings, knowledge):
    app = create_app(
        settings,
        answer_provider=FakeAnswerProvider(),
        reply_gateway=FakeReplyGateway(),
        knowledge=knowledge,
    )
    response = app.test_client().post("/callback", data=_body(), headers={"X-Line-Signature": "bad"})
    assert response.status_code == 400


def test_empty_events_return_200(settings, knowledge):
    body = '{"destination":"U-bot","events":[]}'
    app = create_app(
        settings,
        answer_provider=FakeAnswerProvider(),
        reply_gateway=FakeReplyGateway(),
        knowledge=knowledge,
    )
    response = app.test_client().post(
        "/callback", data=body, headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    )
    assert response.status_code == 200


def test_text_event_replies_once_and_duplicate_is_ignored(settings, knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    provider = FakeAnswerProvider(BotAnswer(card.label, "黑洞已有多種觀測證據。", (card.id,)))
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    body = _body()
    headers = {"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    client = app.test_client()
    assert client.post("/callback", data=body, headers=headers).status_code == 200
    assert client.post("/callback", data=body, headers=headers).status_code == 200
    assert provider.calls == 1
    assert len(gateway.replies) == 1
    assert "【已觀測／已驗證】" in gateway.replies[0][1]


def test_non_text_event_gets_fixed_reply(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    body = _body(message_type="image")
    response = app.test_client().post(
        "/callback", data=body, headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    )
    assert response.status_code == 200
    assert gateway.replies == [("reply-1", UNSUPPORTED_REPLY)]


def test_openai_failure_gets_safe_fallback(settings, knowledge):
    gateway = FakeReplyGateway()
    app = create_app(
        settings,
        answer_provider=FakeAnswerProvider(error=TimeoutError()),
        reply_gateway=gateway,
        knowledge=knowledge,
    )
    body = _body()
    app.test_client().post(
        "/callback", data=body, headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    )
    assert gateway.replies == [("reply-1", SERVICE_ERROR_REPLY)]


def test_reply_failure_is_not_retried_inside_request_and_redelivery_can_retry(settings, knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    provider = FakeAnswerProvider(BotAnswer(card.label, "回答。", (card.id,)))
    gateway = FlakyReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    body = _body()
    headers = {"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    client = app.test_client()
    assert client.post("/callback", data=body, headers=headers).status_code == 500
    assert gateway.attempts == 1
    assert client.post("/callback", data=body, headers=headers).status_code == 200
    assert gateway.attempts == 2
    assert len(gateway.replies) == 1


def test_long_question_is_rejected_without_openai_call(settings, knowledge):
    provider = FakeAnswerProvider()
    gateway = FakeReplyGateway()
    app = create_app(settings, answer_provider=provider, reply_gateway=gateway, knowledge=knowledge)
    body = _body(text="星" * 1001)
    response = app.test_client().post(
        "/callback", data=body, headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)}
    )
    assert response.status_code == 200
    assert provider.calls == 0
    assert gateway.replies == [("reply-1", QUESTION_TOO_LONG_REPLY)]
