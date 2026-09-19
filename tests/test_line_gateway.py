from __future__ import annotations

import pytest

from eternal_polaris.line_gateway import (
    QuickReplyOption,
    _infer_hero_key,
    _resolve_hero_filename,
    build_reply_message,
    build_text_message,
)


def test_quiz_card_preserves_content_and_signed_actions():
    options = tuple(QuickReplyOption(label, data=f"signed-{i}", display_text=f"{letter}. 選項")
                    for i, (label, letter) in enumerate(zip("ⒶⒷⒸⒹ", "ABCD", strict=True)))
    options += (QuickReplyOption("退出", data="ep:quit", display_text="退出"),)
    text = "第一題\n哪個答案正確？\nA. 一\nB. 二\nC. 三\nD. 四"
    payload = build_reply_message(text, options).to_dict()
    assert payload["type"] == "flex"
    assert text in payload["altText"]
    bubble = payload["contents"]
    contents = bubble["body"]["contents"]
    assert contents[1]["text"] == text
    assert contents[1]["wrap"] is True
    assert contents[1]["size"] == "26px"
    assert bubble["body"]["background"]["type"] == "linearGradient"
    assert contents[2]["layout"] == "horizontal"
    buttons = contents[2]["contents"]
    assert len(buttons) == 4
    assert all(button["contents"][0]["size"] == "44px" for button in buttons)
    assert [b["action"]["label"] for b in buttons] == list("ⒶⒷⒸⒹ")
    assert [b["action"]["data"] for b in buttons] == [o.data for o in options[:4]]
    assert contents[3]["action"]["data"] == "ep:quit"
    assert build_reply_message("x" * 2001, options).type == "text"


def test_chat_and_menu_remain_plain_text():
    assert build_reply_message("慢慢說，我在聽。").type == "text"
    assert build_reply_message("選寶庫", (QuickReplyOption("寶庫", data="ep:challenge"),)).type == "text"


def test_guided_learning_route_menu_becomes_flex_and_keeps_quick_replies():
    options = (
        QuickReplyOption("星海之庫", message_text="學習路線 cosmos"),
        QuickReplyOption("地脈與生命", message_text="學習路線 living_world"),
    )
    text = "「你對這世界感到好奇嗎？」\n\n老人攤開星圖，四座寶庫映入眼簾。"
    payload = build_reply_message(text, options).to_dict()
    assert payload["type"] == "flex"
    assert payload["contents"]["body"]["contents"][0]["text"] == "四座寶庫"
    assert [item["action"]["text"] for item in payload["quickReply"]["items"]] == [
        "學習路線 cosmos", "學習路線 living_world",
    ]


def test_guided_lesson_and_answer_become_accessible_flex_cards():
    lesson = "星海之庫 1/4｜認識行星\n第 1/5 段：冥王星為什麼不是行星？"
    lesson_payload = build_reply_message(
        lesson, (QuickReplyOption("理解題", data="learn:signed"),)
    ).to_dict()
    assert lesson_payload["type"] == "flex"
    assert lesson_payload["contents"]["body"]["contents"][0]["text"] == "星海之庫 1/4｜認識行星"
    assert lesson_payload["contents"]["body"]["contents"][2]["scaling"] is True

    answer = "【已觀測／已驗證】\n金星既可在清晨也可在黃昏出現。\n\n來源：NASA"
    answer_payload = build_reply_message(
        answer, (QuickReplyOption("繼續學習", message_text="繼續學習"),)
    ).to_dict()
    assert answer_payload["type"] == "flex"
    assert answer_payload["contents"]["body"]["contents"][0]["text"] == "已觀測／已驗證"
    assert answer_payload["quickReply"]["items"][0]["action"]["text"] == "繼續學習"


def test_flex_card_can_include_https_hero_and_selects_broad_topic():
    text = "【已觀測／已驗證】\n不同恆星下，植物可能演化出不同色素。\n\n來源：NASA"
    payload = build_reply_message(
        text,
        (QuickReplyOption("繼續學習", message_text="繼續學習"),),
        hero_url="https://example.test/media/knowledge/vault-living-world.jpg",
    ).to_dict()
    assert payload["contents"]["hero"]["url"].endswith("vault-living-world.jpg")
    assert payload["contents"]["hero"]["aspectRatio"] == "16:9"
    assert _infer_hero_key(text) == "living_world"
    assert _infer_hero_key("【科幻設定】\n未來城市行星需要龐大散熱系統。") == "future"
    assert _infer_hero_key("一般聊天") is None
    assert _resolve_hero_filename(text, "card-sw085.jpg") == "card-sw085.jpg"
    assert _resolve_hero_filename(text, "not-allowlisted.jpg") == "vault-living-world.jpg"


def test_build_text_message_supports_postback_and_message_actions():
    message = build_text_message(
        "功能",
        (
            QuickReplyOption("接受試煉", data="ep:challenge", display_text="挑戰"),
            QuickReplyOption("問個問題", message_text="黑洞真的存在嗎？"),
        ),
    )
    assert message.text == "功能"
    assert message.quick_reply is not None
    assert len(message.quick_reply.items) == 2
    postback = message.quick_reply.items[0].action
    text_action = message.quick_reply.items[1].action
    assert postback.data == "ep:challenge"
    assert postback.display_text == "挑戰"
    assert text_action.text == "黑洞真的存在嗎？"


def test_quick_reply_requires_exactly_one_action_kind():
    with pytest.raises(ValueError):
        QuickReplyOption("錯誤")
    with pytest.raises(ValueError):
        QuickReplyOption("錯誤", data="x", message_text="y")


def test_line_limits_are_enforced_before_api_call():
    with pytest.raises(ValueError):
        build_text_message("x", tuple(QuickReplyOption(str(i), message_text=str(i)) for i in range(14)))
    with pytest.raises(ValueError):
        build_text_message("x" * 5001)
    with pytest.raises(ValueError):
        QuickReplyOption("x" * 21, message_text="x")
