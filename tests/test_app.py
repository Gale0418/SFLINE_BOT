from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random
import sqlite3
import time

import pytest

from eternal_polaris import persona
from eternal_polaris.answer_service import SERVICE_ERROR_REPLY
from eternal_polaris.app import (
    QUESTION_TOO_LONG_REPLY,
    RATE_LIMIT_REPLY,
    STICKER_FALLBACK_REPLY,
    UNSUPPORTED_REPLY,
    create_app,
)
from eternal_polaris.dispatcher import DurableEventDispatcher, InlineEventDispatcher
from eternal_polaris.memory import RequestRateLimiter
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
        self.hero_filenames = []

    def reply_text(self, reply_token, text, quick_replies=(), *, hero_filename=""):
        self.replies.append((reply_token, text, tuple(quick_replies)))
        self.hero_filenames.append(hero_filename)


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


def _make_app(
    settings,
    knowledge,
    quiz_bank,
    provider=None,
    gateway=None,
    dispatcher=None,
    manager=None,
    rate_limiter=None,
):
    return create_app(
        settings,
        answer_provider=provider or FakeAnswerProvider(),
        reply_gateway=gateway or FakeReplyGateway(),
        knowledge=knowledge,
        quiz_bank=quiz_bank,
        quiz_manager=manager,
        dispatcher=dispatcher or InlineEventDispatcher(),
        rate_limiter=rate_limiter,
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
    assert response.get_json() == {
        "status": "ok",
        "knowledge_cards": 1234,
        "quiz_questions": 300,
    }
    ready = app.test_client().get("/ready")
    assert ready.status_code == 200
    assert ready.get_json() == {"status": "ready"}


def test_serves_only_allowlisted_knowledge_heroes(settings, knowledge, quiz_bank):
    app = _make_app(settings, knowledge, quiz_bank)
    response = app.test_client().get("/media/knowledge/vault-cosmos.jpg")
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert app.test_client().get("/media/knowledge/card-sw009.jpg").status_code == 200
    assert app.test_client().get("/media/knowledge/not-a-card.jpg").status_code == 404


def test_cited_featured_card_selects_its_exact_hero(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    provider = FakeAnswerProvider(BotAnswer(
        ScienceLabel.OBSERVED_VERIFIED,
        "太陽以核心核融合釋放能量。",
        ("sw009",),
    ))
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)

    assert _post(app, _body(text="太陽為什麼會發光？"), settings).status_code == 200
    assert gateway.hero_filenames[-1] == "card-sw009.jpg"


def test_guided_learning_webhook_and_free_question(settings, knowledge, quiz_bank):
    provider = FakeAnswerProvider(error=AssertionError("deterministic steps must not call model"))
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    def send(text, n):
        assert _post(app, _body(text=text, event_id=f"learn-{n}"), settings).status_code == 200
        return gateway.replies[-1]
    assert "你對這世界感到好奇嗎？" in send("學習", 1)[1]
    assert "地脈與生命" in send("學習路線 living_world", 2)[1]
    lesson = send("繼續學習", 3)
    token = lesson[2][0].data
    payload = json.loads(_body(event_id="learn-postback"))
    event = payload["events"][0]
    event["type"] = "postback"
    del event["message"]
    event["postback"] = {"data": token}
    assert _post(app, json.dumps(payload), settings).status_code == 200
    assert "小理解題" in gateway.replies[-1][1]
    assert "理解題完成" in send(quiz_bank.by_id["L001"].correct_letter, 4)[1]
    assert provider.calls == 0
    # Open questions use the existing answer service, without losing lesson state.
    provider.error = None
    provider.result = BotAnswer(ScienceLabel.GENERAL, "天空的藍色主要來自空氣分子對陽光的散射。", ())
    assert "天空" in send("天空為什麼是藍色的？", 5)[1]
    assert "理解題完成" in send("繼續學習", 6)[1]
    assert provider.calls == 1


def test_ten_child_questions_have_correct_sources_and_random_buttons(knowledge, monkeypatch):
    from eternal_polaris.app import (
        CHILD_QUESTIONS,
        _after_answer_options,
        _home_options,
        _rules_options,
    )

    assert len(set(CHILD_QUESTIONS)) == 10
    expected = ["ov024", "ov025", "ov026", "ov027", "ov028", "ov029", "ov030", "ov031", "ov032", "ov033"]
    for question, card_id in zip(CHILD_QUESTIONS, expected, strict=True):
        assert knowledge.match_question(question).id == card_id
        monkeypatch.setattr("eternal_polaris.app.secrets.choice", lambda pool, q=question: q)
        assert next(o for o in _home_options() if o.label == "🔭 問個問題").message_text == question
        assert next(o for o in _after_answer_options() if o.label == "🔭 問個問題").message_text == question
        assert _rules_options()[1].message_text == question


def test_chat_webhook_keeps_only_three_exchanges(settings, knowledge, quiz_bank):
    histories = []

    class ChatProvider:
        def answer(self, question, history):
            histories.append(history)
            return BotAnswer(ScienceLabel.CHAT, "我在聽，請繼續說。", ())

    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=ChatProvider(), gateway=gateway)
    messages = ["今天有點累", "我在準備專題", "擔心上台忘詞", "你好", "記得我擔心什麼嗎"]
    for index, text in enumerate(messages):
        assert _post(app, _body(event_id=f"chat-{index}", text=text), settings).status_code == 200
    assert [len(history) for history in histories] == [0, 1, 2, 3, 3]
    assert [item.user for item in histories[-1]] == messages[1:4]
    assert all(reply[1] == "我在聽，請繼續說。" for reply in gateway.replies)


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
    assert len(gateway.replies[0][2]) == 4


@pytest.mark.parametrize("text", ["你好", "您好！", "Hello!", "👋", "❤️", "(｀・ω・´)ゞ"])
def test_greeting_skips_unavailable_model(settings, knowledge, quiz_bank, text):
    provider = FakeAnswerProvider(error=TimeoutError())
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    assert _post(app, _body(text=text), settings).status_code == 200
    assert provider.calls == 0
    assert "永恆北極星" in gateway.replies[0][1]
    assert len(gateway.replies[0][2]) == 4


def test_greeting_preserves_active_quiz(settings, knowledge, quiz_bank):
    manager = QuizManager(quiz_bank, salt=settings.line_channel_secret)
    session = manager.start("U-test", vault="cosmos", difficulty="easy")
    provider = FakeAnswerProvider(error=TimeoutError())
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway, manager=manager)
    _post(app, _body(text="你好"), settings)
    assert "試煉尚未結束" in gateway.replies[0][1]
    assert manager.current("U-test") is session
    assert provider.calls == 0


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
    options = gateway.replies[0][2]
    assert [option.label for option in options[:4]] == list("ⒶⒷⒸⒹ")
    assert all(option.data for option in options[:4])
    assert options[4].data == "ep:quit"
    session = manager.current("U-test")
    assert session is not None
    for letter, choice, option in zip("ABCD", session.current_question.choices, options[:4], strict=True):
        assert f"{letter}. {choice}" in gateway.replies[0][1]
        assert option.display_text == f"{letter}. {choice}"


def test_non_text_event_gets_fixed_reply(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, gateway=gateway)
    _post(app, _body(message_type="image"), settings)
    assert gateway.replies[0][1] == UNSUPPORTED_REPLY
    assert any(option.message_text == "首頁" or option.message_text == "幫助" for option in gateway.replies[0][2])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("quq", "心情縮成一小團"),
        ("OWO/", "星光很有精神"),
        ("[folded]", STICKER_FALLBACK_REPLY),
    ],
)
def test_emoticons_and_desktop_sticker_fallback_reply_locally(
    settings, knowledge, quiz_bank, text, expected
):
    provider = FakeAnswerProvider(error=AssertionError("casual symbols must not call the model"))
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    _post(app, _body(text=text), settings)
    assert expected in gateway.replies[0][1]
    assert provider.calls == 0


def test_group_rejection_has_no_unusable_recovery_buttons(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    app = _make_app(settings, knowledge, quiz_bank, gateway=gateway)
    _post(app, _body(source_type="group"), settings)
    assert gateway.replies[0][1] == UNSUPPORTED_REPLY
    assert gateway.replies[0][2] == ()


def test_rate_limit_stops_model_and_returns_recovery_options(settings, knowledge, quiz_bank):
    provider = FakeAnswerProvider(error=AssertionError("rate-limited request must not call model"))
    gateway = FakeReplyGateway()
    limiter = RequestRateLimiter(
        salt="salt", per_user_per_minute=1, global_per_minute=1
    )
    assert limiter.allow("U-test")
    app = _make_app(
        settings,
        knowledge,
        quiz_bank,
        provider=provider,
        gateway=gateway,
        rate_limiter=limiter,
    )
    _post(app, _body(), settings)
    assert gateway.replies[-1][1] == RATE_LIMIT_REPLY
    assert gateway.replies[-1][2]
    assert provider.calls == 0


def test_durable_app_retries_sqlite_failure_before_reply(
    settings, knowledge, quiz_bank, tmp_path
):
    class FlakyLearning:
        def __init__(self):
            self.calls = 0

        def handle(self, user_id, text, *, postback=False):
            del user_id, text, postback
            self.calls += 1
            if self.calls == 1:
                raise sqlite3.OperationalError("temporarily locked")
            return "資料庫恢復後已繼續。", ()

        def pause(self, user_id):
            del user_id

        def ready(self):
            return True

    learning = FlakyLearning()
    gateway = FakeReplyGateway()
    dispatcher = DurableEventDispatcher(tmp_path / "retry-app.sqlite3", max_workers=1)
    app = create_app(
        settings,
        answer_provider=FakeAnswerProvider(),
        reply_gateway=gateway,
        knowledge=knowledge,
        quiz_bank=quiz_bank,
        dispatcher=dispatcher,
        learning_manager=learning,
    )
    assert _post(app, _body(text="學習", event_id="sqlite-retry"), settings).status_code == 200
    deadline = time.time() + 3
    while not gateway.replies and time.time() < deadline:
        time.sleep(0.02)
    dispatcher.shutdown(wait=True)
    assert learning.calls == 2
    assert gateway.replies[-1][1] == "資料庫恢復後已繼續。"


def test_home_command_exits_quiz_and_returns_menu(settings, knowledge, quiz_bank):
    manager = QuizManager(quiz_bank, salt=settings.line_channel_secret)
    manager.start("U-test", vault="cosmos", difficulty="easy")
    gateway = FakeReplyGateway()
    provider = FakeAnswerProvider(error=AssertionError("home must not call model"))
    app = _make_app(
        settings, knowledge, quiz_bank, provider=provider, gateway=gateway, manager=manager
    )
    _post(app, _body(text="返回首頁"), settings)
    assert manager.current("U-test") is None
    assert "永恆北極星" in gateway.replies[-1][1]
    assert provider.calls == 0


def test_typed_letter_without_active_quiz_never_calls_model(settings, knowledge, quiz_bank):
    gateway = FakeReplyGateway()
    provider = FakeAnswerProvider(error=AssertionError("expired answer must not call model"))
    app = _make_app(settings, knowledge, quiz_bank, provider=provider, gateway=gateway)
    _post(app, _body(text="A"), settings)
    assert gateway.replies[-1][1] == persona.QUIZ_EXPIRED_TEXT
    assert provider.calls == 0


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
