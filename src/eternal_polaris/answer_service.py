from __future__ import annotations

import json
from typing import Protocol

from openai import OpenAI

from .knowledge import KnowledgeBase
from .models import BotAnswer, Exchange, ScienceLabel


OUT_OF_SCOPE_REPLY = (
    "這個問題已經走到我收藏的星圖之外了。"
    "我目前專注於天文、地球、生命科學、物理、未來科技，以及可與現實科學對照的科幻概念。"
    "換個方向問我黑洞、地震、演化、量子、能源、曲速或蟲洞吧。"
)
SERVICE_ERROR_REPLY = "宇宙訊號暫時受到了干擾。先別急，過一會兒再問我一次吧。"


class AnswerProvider(Protocol):
    def answer(self, question: str, history: tuple[Exchange, ...]) -> BotAnswer: ...


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": [label.value for label in ScienceLabel]},
        "answer": {"type": "string", "minLength": 1, "maxLength": 700},
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
        timeout_seconds: float = 5.0,
        client: OpenAI | None = None,
    ) -> None:
        self._client = client or OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self._model = model
        self._knowledge = knowledge
        self._instructions = self._build_instructions()

    def _build_instructions(self) -> str:
        return (
            "你是『永恆北極星』，一位溫和、博學、從容的年長星空導覽者。"
            "使用繁體中文（台灣用語），先講結論，再用 2 到 4 句清楚解釋。"
            "長輩感來自耐心與判斷，不要每句稱呼孩子、不要堆砌古風台詞，也不要自稱有意識。"
            "對誤解要溫和糾正，對未知與限制要明說；不得用術語煙霧掩飾。"
            "只能使用下列知識卡的事實，不得使用即時網路、內部常識或捏造資料。"
            "若問題不屬於天文、地球與生命科學、物理、未來科技或科幻物理，"
            "label 必須是 out_of_scope，source_ids 必須為空陣列。"
            "範圍內回答只能引用真正支持答案的卡片 ID。"
            "observed_verified 代表已有觀測或實驗證據；theoretical_unrealized 代表有理論描述但未實現；"
            "science_fiction 代表作品設定或超出現有理論支持。若比較多種狀態，先逐項說清楚，再選主要結論作 label。\n\n"
            "知識卡：\n" + self._knowledge.prompt_context()
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
            max_output_tokens=350,
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
            source_ids=tuple(str(value) for value in raw["source_ids"]),
            route="model",
        )
        return self._knowledge.validate_answer(answer)


class HybridAnswerService:
    """Use a deterministic knowledge-card answer when confidence is high."""

    def __init__(
        self,
        model_service: AnswerProvider,
        knowledge: KnowledgeBase,
        *,
        min_score: float = 0.46,
        min_margin: float = 0.08,
    ) -> None:
        self._model_service = model_service
        self._knowledge = knowledge
        self._min_score = min_score
        self._min_margin = min_margin

    def answer(self, question: str, history: tuple[Exchange, ...]) -> BotAnswer:
        card = self._knowledge.match_question(
            question,
            min_score=self._min_score,
            min_margin=self._min_margin,
        )
        if card is not None:
            return BotAnswer(
                label=card.label,
                answer="".join(card.facts),
                source_ids=(card.id,),
                route="local",
            )
        return self._model_service.answer(question, history)


def render_answer(answer: BotAnswer, knowledge: KnowledgeBase) -> str:
    from .models import LABEL_TITLES

    if answer.label is ScienceLabel.OUT_OF_SCOPE:
        return f"【{LABEL_TITLES[answer.label]}】\n{OUT_OF_SCOPE_REPLY}"
    sources = "、".join(knowledge.source_names(answer.source_ids))
    return f"【{LABEL_TITLES[answer.label]}】\n{answer.answer}\n\n來源：{sources}"
