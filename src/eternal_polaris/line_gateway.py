from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessageAction,
    MessagingApi,
    PostbackAction,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)

from .knowledge_images import FEATURED_IMAGE_FILES

HERO_FILES = {
    "cosmos": "vault-cosmos.jpg",
    "living_world": "vault-living-world.jpg",
    "laws": "vault-laws.jpg",
    "future": "vault-future.jpg",
}


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
        *,
        hero_filename: str = "",
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


def build_reply_message(
    text: str, quick_replies: Sequence[QuickReplyOption] = (), *, hero_url: str = ""
) -> TextMessage | FlexMessage:
    """Add presentation without changing the deterministic action contract."""
    plain = build_text_message(text, quick_replies)
    is_quiz = not (
        len(quick_replies) != 5
        or tuple(option.label for option in quick_replies[:4]) != tuple("ⒶⒷⒸⒹ")
        or any(option.data is None for option in quick_replies)
        or quick_replies[4].data != "ep:quit"
        or len(text) > 2000
    )

    if not is_quiz:
        card = _card_presentation(text, quick_replies)
        if card is None or len(text) > 2400:
            return plain
        title, accent = card
        container = {
            "type": "bubble", "size": "giga",
            "body": {
                "type": "box", "layout": "vertical", "backgroundColor": "#EAF6FF",
                "background": {
                    "type": "linearGradient", "angle": "155deg",
                    "startColor": "#F8FCFF", "centerColor": "#E3F3FF",
                    "endColor": "#CFE8F7", "centerPosition": "55%",
                },
                "paddingAll": "18px", "spacing": "lg", "contents": [
                    {"type": "text", "text": title, "color": accent,
                     "weight": "bold", "size": "28px", "wrap": True,
                     "scaling": True},
                    {"type": "separator", "color": "#9EC3DC"},
                    {"type": "text", "text": text, "color": "#17324D",
                     "size": "19px", "wrap": True, "scaling": True},
                    {"type": "text", "text": "可使用下方按鈕繼續探索",
                     "color": "#55758D", "size": "14px", "wrap": True,
                     "scaling": True},
                ],
            },
        }
        if hero_url:
            container["hero"] = {
                "type": "image", "url": hero_url, "size": "full",
                "aspectRatio": "16:9", "aspectMode": "cover",
            }
        return FlexMessage(
            alt_text=text if len(text) <= 1500 else text[:1499] + "…",
            contents=FlexContainer.from_dict(container),
            quick_reply=plain.quick_reply,
        )

    def button(option: QuickReplyOption, *, exit_button: bool = False) -> dict:
        action = {
            "type": "postback", "label": "退出試煉" if exit_button else option.label,
            "data": option.data, "displayText": option.display_text or option.label,
        }
        if not exit_button:
            return {
                "type": "box", "layout": "vertical", "flex": 1,
                "paddingAll": "4px", "paddingTop": "12px", "paddingBottom": "12px",
                "cornerRadius": "12px",
                "borderWidth": "1px", "borderColor": "#B59B65",
                "backgroundColor": "#182C46", "action": action,
                "contents": [{
                    "type": "text", "text": option.label, "size": "44px",
                    "color": "#F2D89C", "weight": "bold", "align": "center",
                    "wrap": True,
                }],
            }
        return {
            "type": "button", "style": "link", "height": "md",
            "color": "#B8CCE4", "action": action,
        }

    container = {
        "type": "bubble", "size": "giga",
        "body": {
            "type": "box", "layout": "vertical", "backgroundColor": "#EAF6FF",
            "background": {
                "type": "linearGradient", "angle": "155deg",
                "startColor": "#F8FCFF", "centerColor": "#E3F3FF",
                "endColor": "#CFE8F7", "centerPosition": "55%",
            },
            "paddingAll": "16px", "spacing": "xl", "contents": [
                {"type": "text", "text": "星之試煉", "color": "#80551B",
                 "weight": "bold", "size": "32px", "wrap": True},
                {"type": "text", "text": text, "color": "#17324D",
                 "size": "26px", "wrap": True},
                {"type": "box", "layout": "horizontal", "spacing": "sm", "contents": [
                    button(option) for option in quick_replies[:4]
                ]},
                button(quick_replies[4], exit_button=True),
            ],
        },
    }
    if hero_url:
        container["hero"] = {
            "type": "image", "url": hero_url, "size": "full",
            "aspectRatio": "16:9", "aspectMode": "cover",
        }
    return FlexMessage(
        alt_text=(text if len(text) <= 1450 else text[:1449] + "…") + "\n請選 A、B、C、D，或輸入退出。",
        contents=FlexContainer.from_dict(container),
    )


def _card_presentation(
    text: str, quick_replies: Sequence[QuickReplyOption]
) -> tuple[str, str] | None:
    """Choose a visual skin from existing content; never infer a new action."""
    if not quick_replies:
        return None
    if text.startswith("「你對這世界感到好奇嗎？」"):
        return "四座寶庫", "#2F6B5F"
    for line in text.splitlines():
        if "｜" in line and any(
            marker in text
            for marker in ("學習地圖", "第 ", "小理解題", "過關挑戰", "理解題完成", "五段教材已完成")
        ):
            return line.strip(), "#2F6B5F"
    first = text.splitlines()[0].strip() if text.strip() else ""
    if first.startswith("【") and first.endswith("】"):
        return first[1:-1], "#80551B"
    return None


class LineReplyGateway:
    """Send one bounded LINE Reply API request per reply token.

    The Reply API does not expose a retry key. A network-ambiguous retry could
    duplicate a reply, so transport retries are deliberately disabled here.
    """

    def __init__(
        self,
        access_token: str,
        *,
        request_timeout_seconds: float = 2.0,
        public_base_url: str = "",
    ) -> None:
        self._configuration = Configuration(access_token=access_token)
        self._request_timeout_seconds = request_timeout_seconds
        self._public_base_url = public_base_url.rstrip("/")

    def reply_text(
        self,
        reply_token: str,
        text: str,
        quick_replies: Sequence[QuickReplyOption] = (),
        *,
        hero_filename: str = "",
    ) -> None:
        hero_url = ""
        if self._public_base_url:
            filename = _resolve_hero_filename(text, hero_filename)
            if filename:
                hero_url = f"{self._public_base_url}/media/knowledge/{filename}"
        message = build_reply_message(text, quick_replies, hero_url=hero_url)
        with ApiClient(self._configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(reply_token=reply_token, messages=[message]),
                _request_timeout=self._request_timeout_seconds,
            )


def _resolve_hero_filename(text: str, hero_filename: str = "") -> str:
    if hero_filename in FEATURED_IMAGE_FILES:
        return hero_filename
    hero_key = _infer_hero_key(text)
    return HERO_FILES[hero_key] if hero_key else ""


def _infer_hero_key(text: str) -> str | None:
    """Select one broad illustration; the factual card remains the authority."""
    if not _card_presentation(text, (QuickReplyOption("繼續", message_text="繼續"),)):
        return None
    if "地脈與生命" in text or any(word in text for word in (
        "生命", "植物", "生物", "細胞", "DNA", "海洋", "大氣", "地質", "人體", "演化",
    )):
        return "living_world"
    if "萬象法則" in text or any(word in text for word in (
        "量子", "相對論", "重力", "時空", "光速", "電磁", "原子", "能量", "物理定律",
    )):
        return "laws"
    if "未來幻夢" in text or "【科幻設定】" in text or any(word in text for word in (
        "未來", "機器人", "人工智慧", "星際文明", "殖民地", "超光速", "戴森", "城市行星",
    )):
        return "future"
    return "cosmos"
