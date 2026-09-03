from __future__ import annotations

import pytest

from eternal_polaris.commands import Command, normalize_command, route_command


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("幫助", Command.HELP),
        ("你會什麼？", Command.HELP),
        ("出題！", Command.CHALLENGE),
        ("接受 試煉", Command.CHALLENGE),
        ("試煉規則", Command.RULES),
        ("目前成績", Command.SCORE),
        ("停止挑戰", Command.QUIT),
        ("/HELP", Command.HELP),
    ],
)
def test_command_aliases(text, expected):
    assert route_command(text) is expected


def test_command_router_does_not_steal_science_questions():
    assert route_command("挑戰者號太空梭發生了什麼？") is None
    assert route_command("自然選擇會遇到哪些挑戰？") is None
    assert route_command("請解釋費米悖論") is None


def test_normalization_is_nfkc_and_whitespace_insensitive():
    assert normalize_command("  ＨＥＬＰ！！ ") == "help"
