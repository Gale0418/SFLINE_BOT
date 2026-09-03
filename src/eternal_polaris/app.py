from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Sequence

from flask import Flask, Response, abort, jsonify, request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import FollowEvent, MessageEvent, PostbackEvent, TextMessageContent

from . import persona
from .answer_service import (
    SERVICE_ERROR_REPLY,
    AnswerProvider,
    HybridAnswerService,
    OpenAIAnswerService,
    render_answer,
)
from .commands import Command, normalize_command, route_command
from .config import Settings
from .dispatcher import EventDispatcher, ThreadPoolEventDispatcher
from .knowledge import KnowledgeBase
from .line_gateway import LineReplyGateway, QuickReplyOption, ReplyGateway
from .memory import ConversationMemory, EventDeduplicator
from .quiz import (
    DIFFICULTY_NAMES,
    LETTERS,
    VAULTS,
    QuizBank,
    QuizError,
    QuizManager,
    QuizSession,
    answer_postback_data,
)


UNSUPPORTED_REPLY = "我目前只看得懂一對一聊天室中的文字訊息。圖片與群組試煉，先留給下一張星圖吧。"
QUESTION_TOO_LONG_REPLY = "這段訊息太長了。請把問題縮短到 1000 個字以內，我們再慢慢談。"
EMPTY_MESSAGE_REPLY = "我似乎只聽見了一陣安靜。寫下一個天文問題，或說『挑戰』敲響寶庫吧。"
BUSY_REPLY = "Busy"


def create_app(
    settings: Settings | None = None,
    *,
    parser: Any | None = None,
    answer_provider: AnswerProvider | None = None,
    reply_gateway: ReplyGateway | None = None,
    knowledge: KnowledgeBase | None = None,
    quiz_bank: QuizBank | None = None,
    quiz_manager: QuizManager | None = None,
    memory: ConversationMemory | None = None,
    deduplicator: EventDeduplicator | None = None,
    dispatcher: EventDispatcher | None = None,
) -> Flask:
    settings = settings or Settings.from_env()
    knowledge = knowledge or KnowledgeBase.load(_resolve_path(settings.knowledge_path))
    quiz_bank = quiz_bank or QuizBank.load(_resolve_path(settings.quiz_path))
    parser = parser or WebhookParser(settings.line_channel_secret)
    if answer_provider is None:
        model_service = OpenAIAnswerService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            knowledge=knowledge,
            timeout_seconds=settings.openai_timeout_seconds,
        )
        answer_provider = HybridAnswerService(
            model_service,
            knowledge,
            min_score=settings.direct_match_min_score,
            min_margin=settings.direct_match_min_margin,
        )
    reply_gateway = reply_gateway or LineReplyGateway(
        settings.line_channel_access_token,
        request_timeout_seconds=settings.line_reply_timeout_seconds,
    )
    memory = memory or ConversationMemory(
        salt=settings.line_channel_secret,
        ttl_seconds=settings.memory_ttl_seconds,
    )
    deduplicator = deduplicator or EventDeduplicator(settings.dedupe_ttl_seconds)
    quiz_manager = quiz_manager or QuizManager(
        quiz_bank,
        salt=settings.line_channel_secret,
        ttl_seconds=settings.quiz_ttl_seconds,
    )
    dispatcher = dispatcher or ThreadPoolEventDispatcher(
        max_workers=settings.webhook_worker_threads,
        queue_capacity=settings.webhook_queue_capacity,
        max_pending_per_key=settings.webhook_max_pending_per_key,
        key_fn=lambda event: _event_key(event, settings.line_channel_secret),
    )

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.logger.setLevel(logging.INFO)
    app.extensions["event_dispatcher"] = dispatcher

    def process_event(event: Any) -> None:
        _handle_event(
            event=event,
            answer_provider=answer_provider,
            reply_gateway=reply_gateway,
            knowledge=knowledge,
            memory=memory,
            deduplicator=deduplicator,
            quiz_manager=quiz_manager,
            logger=app.logger,
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok", quiz_questions=len(quiz_bank.questions)), 200

    @app.post("/callback")
    def callback():
        signature = request.headers.get("X-Line-Signature", "")
        if not signature:
            abort(400)
        body = request.get_data(as_text=True)
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            app.logger.warning("event=webhook_rejected reason=invalid_signature")
            abort(400)
        except Exception as exc:
            app.logger.warning(
                "event=webhook_rejected reason=parse_error error_type=%s",
                type(exc).__name__,
            )
            abort(400)
        if not dispatcher.submit_many(events, process_event):
            app.logger.warning("event=webhook_rejected reason=worker_capacity")
            return Response(BUSY_REPLY, status=503, mimetype="text/plain")
        return Response("OK", status=200, mimetype="text/plain")

    return app


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, Path(__file__).resolve().parents[2] / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _event_key(event: Any, salt: str) -> str:
    source = getattr(event, "source", None)
    source_type = str(getattr(source, "type", "") or "")
    identity = (
        getattr(source, "user_id", None)
        or getattr(source, "group_id", None)
        or getattr(source, "room_id", None)
        or getattr(event, "webhook_event_id", None)
        or "anonymous"
    )
    return hashlib.sha256(f"{salt}:{source_type}:{identity}".encode("utf-8")).hexdigest()


def _handle_event(
    *,
    event: Any,
    answer_provider: AnswerProvider,
    reply_gateway: ReplyGateway,
    knowledge: KnowledgeBase,
    memory: ConversationMemory,
    deduplicator: EventDeduplicator,
    quiz_manager: QuizManager,
    logger: logging.Logger,
) -> None:
    event_id = str(getattr(event, "webhook_event_id", "") or "")
    if not deduplicator.first_seen(event_id):
        logger.info("event=webhook_ignored reason=duplicate")
        return
    reply_token = str(getattr(event, "reply_token", "") or "")
    if not reply_token:
        logger.info("event=webhook_ignored reason=missing_reply_token")
        return

    source = getattr(event, "source", None)
    source_type = str(getattr(source, "type", "") or "")
    user_id = str(getattr(source, "user_id", "") or "")
    try:
        if source_type != "user" or not user_id:
            _reply(reply_gateway, reply_token, UNSUPPORTED_REPLY)
            logger.info("event=reply_sent category=unsupported_source")
            return
        if isinstance(event, FollowEvent):
            _reply(reply_gateway, reply_token, persona.WELCOME_TEXT, _home_options())
            logger.info("event=reply_sent category=welcome")
            return
        if isinstance(event, PostbackEvent):
            _handle_postback(event, user_id, reply_token, reply_gateway, quiz_manager, logger)
            return
        if not isinstance(event, MessageEvent) or not isinstance(event.message, TextMessageContent):
            _reply(reply_gateway, reply_token, UNSUPPORTED_REPLY)
            logger.info("event=reply_sent category=unsupported_message")
            return
        text = event.message.text.strip()
        if not text:
            _reply(reply_gateway, reply_token, EMPTY_MESSAGE_REPLY, _home_options())
            logger.info("event=reply_sent category=empty_message")
            return
        if len(text) > 1000:
            _reply(reply_gateway, reply_token, QUESTION_TOO_LONG_REPLY)
            logger.info("event=reply_sent category=question_too_long")
            return
        _handle_text(
            text=text,
            user_id=user_id,
            reply_token=reply_token,
            answer_provider=answer_provider,
            reply_gateway=reply_gateway,
            knowledge=knowledge,
            memory=memory,
            quiz_manager=quiz_manager,
            logger=logger,
        )
    except Exception as exc:
        deduplicator.forget(event_id)
        logger.error("event=processing_failed error_type=%s", type(exc).__name__)
        raise


def _handle_text(
    *,
    text: str,
    user_id: str,
    reply_token: str,
    answer_provider: AnswerProvider,
    reply_gateway: ReplyGateway,
    knowledge: KnowledgeBase,
    memory: ConversationMemory,
    quiz_manager: QuizManager,
    logger: logging.Logger,
) -> None:
    command = route_command(text)
    if command is Command.HELP:
        _reply(reply_gateway, reply_token, persona.HELP_TEXT, _home_options())
        logger.info("event=reply_sent category=help")
        return
    if command is Command.CHALLENGE:
        _reply(reply_gateway, reply_token, persona.CHALLENGE_INTRO_TEXT, _vault_options())
        logger.info("event=reply_sent category=quiz_menu")
        return
    if command is Command.RULES:
        _reply(reply_gateway, reply_token, persona.RULES_TEXT, _rules_options())
        logger.info("event=reply_sent category=quiz_rules")
        return
    if command is Command.SCORE:
        session = quiz_manager.current(user_id)
        if session is None:
            _reply(reply_gateway, reply_token, persona.NO_ACTIVE_QUIZ_TEXT, _home_options())
        else:
            _reply(
                reply_gateway,
                reply_token,
                persona.render_score(
                    answered=session.answered,
                    total=session.total,
                    score=session.score,
                    streak=session.best_streak,
                ),
                _answer_options(quiz_manager, user_id, session),
            )
        logger.info("event=reply_sent category=quiz_score")
        return
    if command is Command.QUIT:
        quiz_manager.quit(user_id)
        _reply(reply_gateway, reply_token, persona.QUIT_TEXT, _home_options())
        logger.info("event=reply_sent category=quiz_quit")
        return

    session = quiz_manager.current(user_id)
    answer_letter = normalize_command(text).upper()
    if session is not None:
        if answer_letter in LETTERS:
            try:
                outcome = quiz_manager.submit_text(user_id, answer_letter)
            except QuizError:
                _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, _answer_options(quiz_manager, user_id, session))
                return
            _reply_quiz_outcome(reply_gateway, reply_token, quiz_manager, user_id, outcome)
            logger.info("event=reply_sent category=quiz_answer_typed correct=%s", outcome.correct)
            return
        reminder = (
            "試煉尚未結束。先回答眼前這道門吧；你可以按下選項，或直接輸入 A、B、C、D。\n\n"
            + _render_session_question(session)
        )
        _reply(reply_gateway, reply_token, reminder, _answer_options(quiz_manager, user_id, session))
        logger.info("event=reply_sent category=quiz_reminder")
        return

    started = time.monotonic()
    answer = None
    try:
        history = memory.get(user_id)
        answer = answer_provider.answer(text, history)
        rendered = render_answer(answer, knowledge)
    except Exception as exc:
        logger.error("event=answer_failed category=service_error error_type=%s", type(exc).__name__)
        rendered = SERVICE_ERROR_REPLY
    _reply(reply_gateway, reply_token, rendered, _after_answer_options())
    if answer is not None:
        memory.add(user_id, text, rendered)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "event=reply_sent category=%s route=%s latency_ms=%d",
            answer.label.value,
            answer.route,
            elapsed_ms,
        )
    else:
        logger.info("event=reply_sent category=service_error")


def _handle_postback(
    event: PostbackEvent,
    user_id: str,
    reply_token: str,
    reply_gateway: ReplyGateway,
    quiz_manager: QuizManager,
    logger: logging.Logger,
) -> None:
    data = str(getattr(event.postback, "data", "") or "")
    if data == "ep:challenge":
        _reply(reply_gateway, reply_token, persona.CHALLENGE_INTRO_TEXT, _vault_options())
        return
    if data == "ep:rules":
        _reply(reply_gateway, reply_token, persona.RULES_TEXT, _rules_options())
        return
    if data == "ep:quit":
        quiz_manager.quit(user_id)
        _reply(reply_gateway, reply_token, persona.QUIT_TEXT, _home_options())
        return
    if data.startswith("ep:vault:"):
        vault = data.removeprefix("ep:vault:")
        if vault not in VAULTS:
            _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, _vault_options())
            return
        info = VAULTS[vault]
        text = f"你選擇了 {info.name}。\n{info.description}\n\n現在，決定要敲響哪一種難度的鐘。"
        _reply(reply_gateway, reply_token, text, _difficulty_options(vault))
        return
    if data.startswith("ep:start:"):
        parts = data.split(":")
        if len(parts) != 4:
            _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, _vault_options())
            return
        _, _, vault, difficulty = parts
        try:
            session = quiz_manager.start(user_id, vault=vault, difficulty=difficulty)
        except QuizError:
            _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, _vault_options())
            return
        opening = (
            "星圖上的光匯聚成第一道門。守門人抬手示意。\n"
            "「很好。從現在起，每個答案都會留下痕跡。」\n\n"
            + _render_session_question(session)
        )
        _reply(reply_gateway, reply_token, opening, _answer_options(quiz_manager, user_id, session))
        logger.info("event=reply_sent category=quiz_started vault=%s difficulty=%s", vault, difficulty)
        return
    if data.startswith("ep:a:"):
        session = quiz_manager.current(user_id)
        if session is None:
            _reply(reply_gateway, reply_token, persona.QUIZ_EXPIRED_TEXT, _home_options())
            return
        try:
            outcome = quiz_manager.submit_postback(user_id, data)
        except QuizError:
            current = quiz_manager.current(user_id)
            options = _answer_options(quiz_manager, user_id, current) if current else _home_options()
            _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, options)
            return
        _reply_quiz_outcome(reply_gateway, reply_token, quiz_manager, user_id, outcome)
        logger.info("event=reply_sent category=quiz_answer correct=%s", outcome.correct)
        return
    _reply(reply_gateway, reply_token, persona.INVALID_TOKEN_TEXT, _home_options())


def _reply_quiz_outcome(
    reply_gateway: ReplyGateway,
    reply_token: str,
    quiz_manager: QuizManager,
    user_id: str,
    outcome: Any,
) -> None:
    question = outcome.question
    feedback = persona.render_feedback(
        correct=outcome.correct,
        chosen_letter=outcome.chosen_letter,
        correct_letter=question.correct_letter,
        correct_text=question.correct_text,
        explanation=question.explanation,
        source_name=f"{question.source_name}\n{question.source_url}",
        score=outcome.score,
        answered=outcome.answered,
        total=outcome.total,
    )
    if outcome.completed:
        text = feedback + "\n\n" + persona.render_final(
            score=outcome.score,
            total=outcome.total,
            best_streak=outcome.best_streak,
        )
        _reply(reply_gateway, reply_token, text, _home_options())
        return
    session = quiz_manager.current(user_id)
    if session is None:
        _reply(reply_gateway, reply_token, persona.QUIZ_EXPIRED_TEXT, _home_options())
        return
    text = feedback + "\n\n—— 下一道星門 ——\n\n" + _render_session_question(session)
    _reply(reply_gateway, reply_token, text, _answer_options(quiz_manager, user_id, session))


def _render_session_question(session: QuizSession) -> str:
    info = VAULTS[session.vault]
    return persona.render_question(
        vault_name=info.name,
        number=session.index + 1,
        total=session.total,
        difficulty_name=DIFFICULTY_NAMES[session.difficulty],
        question=session.current_question.prompt,
        choices=session.current_question.choices,
    )


def _reply(
    gateway: ReplyGateway,
    token: str,
    text: str,
    options: Sequence[QuickReplyOption] = (),
) -> None:
    gateway.reply_text(token, text, options)


def _home_options() -> tuple[QuickReplyOption, ...]:
    return (
        QuickReplyOption("🔭 問個問題", message_text="黑洞真的存在嗎？"),
        QuickReplyOption("🗝️ 接受試煉", data="ep:challenge", display_text="挑戰"),
        QuickReplyOption("📜 查看功能", message_text="幫助"),
    )


def _after_answer_options() -> tuple[QuickReplyOption, ...]:
    return (
        QuickReplyOption("🗝️ 接受試煉", data="ep:challenge", display_text="挑戰"),
        QuickReplyOption("📜 查看功能", message_text="幫助"),
    )


def _rules_options() -> tuple[QuickReplyOption, ...]:
    return (
        QuickReplyOption("🗝️ 開始試煉", data="ep:challenge", display_text="挑戰"),
        QuickReplyOption("🔭 回到問答", message_text="黑洞真的存在嗎？"),
    )


def _vault_options() -> tuple[QuickReplyOption, ...]:
    return tuple(
        QuickReplyOption(info.name[:20], data=f"ep:vault:{key}", display_text=info.name)
        for key, info in VAULTS.items()
    ) + (QuickReplyOption("📜 試煉規則", data="ep:rules", display_text="試煉規則"),)


def _difficulty_options(vault: str) -> tuple[QuickReplyOption, ...]:
    icons = {"easy": "🌱", "medium": "🧭", "hard": "🗿", "mixed": "🎲"}
    return tuple(
        QuickReplyOption(
            f"{icons[key]} {name}",
            data=f"ep:start:{vault}:{key}",
            display_text=f"{VAULTS[vault].name}｜{name}",
        )
        for key, name in DIFFICULTY_NAMES.items()
    ) + (QuickReplyOption("↩️ 換座寶庫", data="ep:challenge", display_text="換座寶庫"),)


def _answer_options(
    quiz_manager: QuizManager,
    user_id: str,
    session: QuizSession,
) -> tuple[QuickReplyOption, ...]:
    options: list[QuickReplyOption] = []
    for letter, choice in zip(LETTERS, session.current_question.choices, strict=True):
        label = f"{letter}｜{choice}"
        if len(label) > 20:
            label = label[:19] + "…"
        options.append(
            QuickReplyOption(
                label,
                data=answer_postback_data(quiz_manager, user_id, session, letter),
                display_text=f"{letter}. {choice}",
            )
        )
    options.append(QuickReplyOption("🚪 退出試煉", data="ep:quit", display_text="退出"))
    return tuple(options)
