from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random

from eternal_polaris.app import create_app
from eternal_polaris.dispatcher import InlineEventDispatcher
from eternal_polaris.quiz import QuizManager, answer_postback_data


class NoModel:
    def answer(self, question, history):
        raise AssertionError("quiz control routes must not call the model")


class Gateway:
    def __init__(self):
        self.replies = []

    def reply_text(self, token, text, quick_replies=()):
        self.replies.append((token, text, tuple(quick_replies)))


def _signature(body: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _event_body(event_type: str, *, data: str = "", text: str = "", event_id: str = "evt") -> str:
    event = {
        "type": event_type,
        "mode": "active",
        "timestamp": 1700000000000,
        "source": {"type": "user", "userId": "U-test"},
        "webhookEventId": event_id,
        "deliveryContext": {"isRedelivery": False},
        "replyToken": f"reply-{event_id}",
    }
    if event_type == "postback":
        event["postback"] = {"data": data}
    elif event_type == "message":
        event["message"] = {"id": "m-1", "type": "text", "text": text, "quoteToken": "q-1"}
    payload = {"destination": "U-bot", "events": [event]}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _post(app, settings, body):
    return app.test_client().post(
        "/callback",
        data=body,
        headers={"X-Line-Signature": _signature(body, settings.line_channel_secret)},
    )


def _app(settings, knowledge, quiz_bank):
    gateway = Gateway()
    manager = QuizManager(
        quiz_bank,
        salt=settings.line_channel_secret,
        random_source=random.Random(17),
    )
    app = create_app(
        settings,
        answer_provider=NoModel(),
        reply_gateway=gateway,
        knowledge=knowledge,
        quiz_bank=quiz_bank,
        quiz_manager=manager,
        dispatcher=InlineEventDispatcher(),
    )
    return app, gateway, manager


def test_follow_event_introduces_bot_and_actions(settings, knowledge, quiz_bank):
    app, gateway, _ = _app(settings, knowledge, quiz_bank)
    response = _post(app, settings, _event_body("follow", event_id="follow-1"))
    assert response.status_code == 200
    assert "永恆北極星" in gateway.replies[-1][1]
    assert len(gateway.replies[-1][2]) == 3


def test_postback_menu_vault_start_answer_and_quit(settings, knowledge, quiz_bank):
    app, gateway, manager = _app(settings, knowledge, quiz_bank)

    _post(app, settings, _event_body("postback", data="ep:challenge", event_id="p1"))
    assert len(gateway.replies[-1][2]) == 6

    _post(app, settings, _event_body("postback", data="ep:vault:cosmos", event_id="p2"))
    assert "星海之庫" in gateway.replies[-1][1]
    assert len(gateway.replies[-1][2]) == 5

    _post(app, settings, _event_body("postback", data="ep:start:cosmos:easy", event_id="p3"))
    assert "第 1 / 5 道星門" in gateway.replies[-1][1]
    assert len(gateway.replies[-1][2]) == 5

    session = manager.current("U-test")
    assert session is not None
    token = answer_postback_data(manager, "U-test", session, session.current_question.correct_letter)
    _post(app, settings, _event_body("postback", data=token, event_id="p4"))
    assert "答對了" in gateway.replies[-1][1]
    assert "第 2 / 5 道星門" in gateway.replies[-1][1]

    _post(app, settings, _event_body("postback", data="ep:quit", event_id="p5"))
    assert manager.current("U-test") is None
    assert "茶杯" in gateway.replies[-1][1]


def test_rules_score_and_invalid_postback_have_safe_exits(settings, knowledge, quiz_bank):
    app, gateway, manager = _app(settings, knowledge, quiz_bank)
    _post(app, settings, _event_body("postback", data="ep:rules", event_id="r1"))
    assert "五道門" in gateway.replies[-1][1]

    _post(app, settings, _event_body("message", text="分數", event_id="r2"))
    assert "目前沒有" in gateway.replies[-1][1]

    manager.start("U-test", vault="future", difficulty="mixed")
    _post(app, settings, _event_body("message", text="普通問題", event_id="r3"))
    assert "試煉尚未結束" in gateway.replies[-1][1]

    _post(app, settings, _event_body("postback", data="ep:not-real", event_id="r4"))
    assert "不是屬於眼前這道門" in gateway.replies[-1][1]
