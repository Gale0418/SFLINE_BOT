from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .answer_service import SERVICE_ERROR_REPLY, AnswerProvider, OpenAIAnswerService, render_answer
from .config import Settings
from .knowledge import KnowledgeBase
from .line_gateway import LineReplyGateway, ReplyGateway
from .memory import ConversationMemory, EventDeduplicator


UNSUPPORTED_REPLY = "永恆北極星目前只看得懂一對一聊天室中的文字訊息喔。"
QUESTION_TOO_LONG_REPLY = "這段訊息太長啦，請把問題縮短到 1000 個字以內再問我喔。"


def create_app(
    settings: Settings | None = None,
    *,
    parser: Any | None = None,
    answer_provider: AnswerProvider | None = None,
    reply_gateway: ReplyGateway | None = None,
    knowledge: KnowledgeBase | None = None,
    memory: ConversationMemory | None = None,
    deduplicator: EventDeduplicator | None = None,
) -> Flask:
    settings = settings or Settings.from_env()
    knowledge = knowledge or KnowledgeBase.load(_resolve_knowledge_path(settings.knowledge_path))
    parser = parser or WebhookParser(settings.line_channel_secret)
    answer_provider = answer_provider or OpenAIAnswerService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        knowledge=knowledge,
        timeout_seconds=settings.openai_timeout_seconds,
    )
    reply_gateway = reply_gateway or LineReplyGateway(settings.line_channel_access_token)
    memory = memory or ConversationMemory(
        salt=settings.line_channel_secret,
        ttl_seconds=settings.memory_ttl_seconds,
    )
    deduplicator = deduplicator or EventDeduplicator(settings.dedupe_ttl_seconds)

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.logger.setLevel(logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

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
            app.logger.warning("event=webhook_rejected reason=parse_error error_type=%s", type(exc).__name__)
            abort(400)

        for event in events:
            _handle_event(
                event=event,
                answer_provider=answer_provider,
                reply_gateway=reply_gateway,
                knowledge=knowledge,
                memory=memory,
                deduplicator=deduplicator,
                logger=app.logger,
            )
        return "OK", 200

    return app


def _resolve_knowledge_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, Path(__file__).resolve().parents[2] / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _handle_event(
    *,
    event: Any,
    answer_provider: AnswerProvider,
    reply_gateway: ReplyGateway,
    knowledge: KnowledgeBase,
    memory: ConversationMemory,
    deduplicator: EventDeduplicator,
    logger: logging.Logger,
) -> None:
    event_id = str(getattr(event, "webhook_event_id", "") or "")
    if not deduplicator.first_seen(event_id):
        logger.info("event=webhook_ignored reason=duplicate")
        return
    if not isinstance(event, MessageEvent):
        logger.info("event=webhook_ignored reason=unsupported_event")
        return

    reply_token = str(getattr(event, "reply_token", "") or "")
    if not reply_token:
        logger.warning("event=webhook_ignored reason=missing_reply_token")
        return
    source = getattr(event, "source", None)
    source_type = getattr(source, "type", "")
    user_id = str(getattr(source, "user_id", "") or "")
    if source_type != "user" or not user_id or not isinstance(event.message, TextMessageContent):
        try:
            reply_gateway.reply_text(reply_token, UNSUPPORTED_REPLY)
        except Exception:
            deduplicator.forget(event_id)
            raise
        logger.info("event=reply_sent category=unsupported")
        return

    if len(event.message.text) > 1000:
        try:
            reply_gateway.reply_text(reply_token, QUESTION_TOO_LONG_REPLY)
        except Exception:
            deduplicator.forget(event_id)
            raise
        logger.info("event=reply_sent category=question_too_long")
        return

    started = time.monotonic()
    answer = None
    try:
        history = memory.get(user_id)
        answer = answer_provider.answer(event.message.text, history)
        rendered = render_answer(answer, knowledge)
    except Exception as exc:
        logger.error("event=answer_failed category=service_error error_type=%s", type(exc).__name__)
        rendered = SERVICE_ERROR_REPLY

    try:
        reply_gateway.reply_text(reply_token, rendered)
    except Exception as exc:
        deduplicator.forget(event_id)
        logger.error("event=reply_failed error_type=%s", type(exc).__name__)
        raise

    if answer is not None:
        memory.add(user_id, event.message.text, rendered)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info("event=reply_sent category=%s latency_ms=%d", answer.label.value, elapsed_ms)
    else:
        logger.info("event=reply_sent category=service_error")
