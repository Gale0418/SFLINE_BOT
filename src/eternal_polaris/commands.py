from __future__ import annotations

import re
import unicodedata
from enum import StrEnum


class Command(StrEnum):
    GREETING = "greeting"
    HELP = "help"
    CHALLENGE = "challenge"
    RULES = "rules"
    SCORE = "score"
    QUIT = "quit"
    HOME = "home"


def normalize_command(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(r"[！!。．.？?～~]+$", "", normalized)
    return re.sub(r"\s+", "", normalized)


_COMMANDS: dict[Command, frozenset[str]] = {
    Command.GREETING: frozenset({
        "你好", "您好", "嗨", "哈囉", "哈啰", "哈嘍", "早安", "午安", "晚安",
        "hello", "hi", "hey", "(｀・ω・´)ゞ", "(￣▽￣)ゞ", "=w=", "owo",
    }),
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
    Command.HOME: frozenset({
        "首頁", "主页", "主頁", "返回首頁", "返回主页", "回首頁", "回主页",
        "主選單", "主菜单", "home", "/home",
    }),
}


def route_command(text: str) -> Command | None:
    value = normalize_command(text)
    for command, aliases in _COMMANDS.items():
        if value in {normalize_command(alias) for alias in aliases}:
            return command
    # Emoji-only greetings exclude letters and digits so science questions and
    # quiz answer letters retain their normal routing.
    if value and not any(char.isalnum() for char in value) and any(
        unicodedata.category(char) == "So" for char in value
    ):
        return Command.GREETING
    return None
