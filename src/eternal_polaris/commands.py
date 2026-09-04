from __future__ import annotations

import re
import unicodedata
from enum import StrEnum


class Command(StrEnum):
    HELP = "help"
    CHALLENGE = "challenge"
    RULES = "rules"
    SCORE = "score"
    QUIT = "quit"


def normalize_command(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(r"[！!。．.？?～~]+$", "", normalized)
    return re.sub(r"\s+", "", normalized)


_COMMANDS: dict[Command, frozenset[str]] = {
    Command.HELP: frozenset({
        "幫助", "帮助", "功能", "help", "/help", "使用說明", "使用说明",
        "怎麼用", "怎么用", "你會什麼", "你会什么", "你能做什麼", "你能做什么",
    }),
    Command.CHALLENGE: frozenset({
        "挑戰", "挑战", "出題", "出题", "考我", "開始挑戰", "开始挑战",
        "接受試煉", "接受试炼", "試煉", "试炼", "quiz", "/quiz",
    }),
    Command.RULES: frozenset({
        "規則", "规则", "挑戰規則", "挑战规则", "試煉規則", "试炼规则", "玩法",
    }),
    Command.SCORE: frozenset({
        "分數", "分数", "成績", "成绩", "目前成績", "目前成绩", "進度", "进度", "score",
    }),
    Command.QUIT: frozenset({
        "退出", "停止挑戰", "停止挑战", "結束挑戰", "结束挑战", "放棄試煉", "放弃试炼",
        "回到問答", "回到问答", "quit", "/quit",
    }),
}


def route_command(text: str) -> Command | None:
    value = normalize_command(text)
    for command, aliases in _COMMANDS.items():
        if value in aliases:
            return command
    return None
