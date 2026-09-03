from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI

from .knowledge import KnowledgeBase
from .models import BotAnswer, Exchange, ScienceLabel


OUT_OF_SCOPE_REPLY = "這題超出永恆北極星目前的天文與科幻物理範圍。你可以改問黑洞、恆星、相對論、曲速或蟲洞喔！"
SERVICE_ERROR_REPLY = "永恆北極星暫時接收不到宇宙訊號，請稍後再試一次。"


class AnswerProvider(Protocol):
    def answer(self, question: str, history: tuple[Exchange, ...]) -> BotAnswer: ...


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": [label.value for label in ScienceLabel],
        },
        "answer": {"type": "string", "minLength": 1, "maxLength": 600},
        "source_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
    },
    "required": ["label", "answer", "source_ids"],
    "additionalProperties": False,
}


class OpenAIAnswerService:
    def __init__(
        self,
        api_key: str,
        model: str,
        knowledge: KnowledgeBase,
        timeout_seconds: float = 15.0,
        client: OpenAI | None = None,
    ) -> None:
        self._client = client or OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self._model = model
        self._knowledge = knowledge
        self._instructions = self._build_instructions()

    def _build_instructions(self) -> str:
        return (
            "你是『永恆北極星』，只回答天文與科幻物理問題。使用繁體中文（台灣用語），回答 2 到 4 句。"
            "語氣像冷靜親切的星空導覽員：先講結論再解釋，保留一點溫度，但不要浮誇角色扮演、賣萌或自稱有意識。"
            "科學解釋要直接影響讀者的理解；對未知與限制要明說，不用術語煙霧掩飾。"
            "只能使用下列知識卡的事實，不得使用即時網路或捏造資料。"
            "若問題不屬於天文或科幻物理，label 必須是 out_of_scope、source_ids 必須是空陣列。"
            "範圍內回答的 source_ids 只能引用與 label 相同的卡片 ID。"
            "observed_verified 代表已有觀測或實驗證據；theoretical_unrealized 代表有理論基礎但未實現；"
            "science_fiction 代表作品設定或超出現有理論支持。\n\n知識卡：\n"
            + self._knowledge.prompt_context()
        )

    def answer(self, question: str, history: tuple[Exchange, ...]) -> BotAnswer:
        history_text = "\n".join(
            f"使用者：{exchange.user}\n永恆北極星：{exchange.assistant}" for exchange in history
        )
        prompt = f"最近三組對話：\n{history_text or '（無）'}\n\n本次問題：{question}"
        response = self._client.responses.create(
            model=self._model,
            instructions=self._instructions,
            input=prompt,
            max_output_tokens=300,
            reasoning={"effort": "none"},
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "eternal_polaris_answer",
                    "strict": True,
                    "schema": ANSWER_SCHEMA,
                }
            },
        )
        raw = json.loads(response.output_text)
        answer = BotAnswer(
            label=ScienceLabel(raw["label"]),
            answer=str(raw["answer"]).strip(),
            source_ids=tuple(raw["source_ids"]),
        )
        return self._knowledge.validate_answer(answer)


def render_answer(answer: BotAnswer, knowledge: KnowledgeBase) -> str:
    from .models import LABEL_TITLES

    if answer.label is ScienceLabel.OUT_OF_SCOPE:
        return f"【{LABEL_TITLES[answer.label]}】\n{OUT_OF_SCOPE_REPLY}"
    sources = "、".join(knowledge.source_names(answer.source_ids))
    return f"【{LABEL_TITLES[answer.label]}】\n{answer.answer}\n\n來源：{sources}"
