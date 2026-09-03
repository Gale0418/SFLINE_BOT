from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from eternal_polaris import persona
from eternal_polaris.app import create_app
from eternal_polaris.dispatcher import InlineEventDispatcher
from eternal_polaris.knowledge import KnowledgeError
from eternal_polaris.models import BotAnswer
from eternal_polaris.quiz import QuizManager


class NoModel:
    def __init__(self):
        self.calls = 0

    def answer(self, question, history):
        self.calls += 1
        raise AssertionError("model must not run")


class Gateway:
    def __init__(self):
        self.replies = []

    def reply_text(self, token, text, quick_replies=()):
        self.replies.append((token, text, tuple(quick_replies)))


def _signed_text_body(text: str, secret: str) -> tuple[str, dict[str, str]]:
    payload = {
        "destination": "U-bot",
        "events": [
            {
                "type": "message",
                "mode": "active",
                "timestamp": 1700000000000,
                "source": {"type": "user", "userId": "U-test"},
                "webhookEventId": "empty-1",
                "deliveryContext": {"isRedelivery": False},
                "replyToken": "reply-empty",
                "message": {"id": "m-1", "type": "text", "text": text, "quoteToken": "q-1"},
            }
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return body, {"X-Line-Signature": base64.b64encode(digest).decode()}


def test_help_contract_separates_free_qa_from_cross_domain_quiz():
    assert "問我星空與科幻物理" in persona.HELP_TEXT
    assert "試煉橫跨萬象" in persona.HELP_TEXT
    assert "地震" in persona.HELP_TEXT and "演化" in persona.HELP_TEXT


def test_whitespace_message_does_not_spend_model_call(settings, knowledge, quiz_bank):
    model = NoModel()
    gateway = Gateway()
    app = create_app(
        settings,
        answer_provider=model,
        reply_gateway=gateway,
        knowledge=knowledge,
        quiz_bank=quiz_bank,
        dispatcher=InlineEventDispatcher(),
    )
    body, headers = _signed_text_body("   ", settings.line_channel_secret)
    response = app.test_client().post("/callback", data=body, headers=headers)
    assert response.status_code == 200
    assert model.calls == 0
    assert "安靜" in gateway.replies[0][1]


def test_answer_validation_caps_content_and_requires_primary_source(knowledge):
    card = knowledge.cards[0]
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(card.label, "x" * 701, (card.id,)))
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(card.label, "回答", (card.id, card.id, card.id, card.id)))


def test_quiz_manager_rejects_invalid_capacity_settings(quiz_bank):
    with pytest.raises(ValueError):
        QuizManager(quiz_bank, salt="secret", question_count=0)
    with pytest.raises(ValueError):
        QuizManager(quiz_bank, salt="secret", ttl_seconds=0)
    with pytest.raises(ValueError):
        QuizManager(quiz_bank, salt="secret", max_sessions=0)
