from __future__ import annotations

import pytest

from eternal_polaris.line_gateway import QuickReplyOption, build_text_message


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
