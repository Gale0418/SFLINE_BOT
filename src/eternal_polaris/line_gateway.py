from __future__ import annotations

from typing import Protocol

from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage


class ReplyGateway(Protocol):
    def reply_text(self, reply_token: str, text: str) -> None: ...


class LineReplyGateway:
    def __init__(self, access_token: str) -> None:
        self._configuration = Configuration(access_token=access_token)

    def reply_text(self, reply_token: str, text: str) -> None:
        with ApiClient(self._configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)],
                )
            )

