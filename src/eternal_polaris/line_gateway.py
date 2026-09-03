from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessageAction,
    MessagingApi,
    PostbackAction,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)


@dataclass(frozen=True, slots=True)
class QuickReplyOption:
    label: str
    data: str | None = None
    message_text: str | None = None
    display_text: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= len(self.label) <= 20:
            raise ValueError("Quick Reply label 必須為 1 到 20 個字元")
        if (self.data is None) == (self.message_text is None):
            raise ValueError("Quick Reply 必須且只能設定 data 或 message_text")
        if self.data is not None and not 1 <= len(self.data) <= 300:
            raise ValueError("Postback data 必須為 1 到 300 個字元")
        if self.message_text is not None and not 1 <= len(self.message_text) <= 300:
            raise ValueError("MessageAction text 必須為 1 到 300 個字元")
        if self.display_text is not None and not 1 <= len(self.display_text) <= 300:
            raise ValueError("Postback display_text 必須為 1 到 300 個字元")


class ReplyGateway(Protocol):
    def reply_text(
        self,
        reply_token: str,
        text: str,
        quick_replies: Sequence[QuickReplyOption] = (),
    ) -> None: ...


def build_text_message(text: str, quick_replies: Sequence[QuickReplyOption] = ()) -> TextMessage:
    if not 1 <= len(text) <= 5000:
        raise ValueError("LINE 文字訊息必須為 1 到 5000 個字元")
    if len(quick_replies) > 13:
        raise ValueError("LINE Quick Reply 最多 13 個項目")
    items: list[QuickReplyItem] = []
    for option in quick_replies:
        if option.data is not None:
            action = PostbackAction(
                label=option.label,
                data=option.data,
                display_text=option.display_text or option.label,
            )
        else:
            action = MessageAction(label=option.label, text=option.message_text or option.label)
        items.append(QuickReplyItem(action=action))
    quick_reply = QuickReply(items=items) if items else None
    return TextMessage(text=text, quick_reply=quick_reply)


class LineReplyGateway:
    """Send one bounded LINE Reply API request per reply token.

    The Reply API does not expose a retry key. A network-ambiguous retry could
    duplicate a reply, so transport retries are deliberately disabled here.
    """

    def __init__(self, access_token: str, *, request_timeout_seconds: float = 2.0) -> None:
        self._configuration = Configuration(access_token=access_token)
        self._request_timeout_seconds = request_timeout_seconds

    def reply_text(
        self,
        reply_token: str,
        text: str,
        quick_replies: Sequence[QuickReplyOption] = (),
    ) -> None:
        message = build_text_message(text, quick_replies)
        with ApiClient(self._configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(reply_token=reply_token, messages=[message]),
                _request_timeout=self._request_timeout_seconds,
            )
