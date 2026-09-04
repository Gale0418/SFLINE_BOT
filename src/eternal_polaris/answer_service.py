from __future__ import annotations

import json
from typing import Any, Protocol
from urllib.parse import quote

import httpx
from openai import OpenAI

from .knowledge import KnowledgeBase
from .models import BotAnswer, Exchange, ScienceLabel


OUT_OF_SCOPE_REPLY = (
    "這個問題已經走到我目前收藏的星圖之外了。"
    "自由問答現在專注於天文與科幻物理；若想橫跨地球、生命、量子、能源、AI 與太空工程，"
    "可以說『挑戰』進入萬象題庫。"
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

# Gemini structured output supports a JSON Schema subset. String length is
# intentionally enforced locally, while enum/required/maxItems remain useful
# provider-side constraints.
GOOGLE_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": [label.value for label in ScienceLabel]},
        "answer": {"type": "string"},
        "source_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
    },
    "required": ["label", "answer", "source_ids"],
    "additionalProperties": False,
}


def _parse_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    raw = json.loads(cleaned)
    if not isinstance(raw, dict):
        raise ValueError("模型輸出必須是 JSON object")
    return raw


def _google_output_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Google API 未回傳候選答案")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("Google API 回傳格式缺少 content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ValueError("Google API 回傳格式缺少 parts")
    text_parts = [
        str(part["text"])
        for part in parts
        if isinstance(part, dict)
        and not part.get("thought")
        and isinstance(part.get("text"), str)
    ]
    text = "".join(text_parts).strip()
    if not text:
        raise ValueError("Google API 未回傳文字答案")
    return text


class OpenAIAnswerService:
    """Bounded model fallback supporting OpenAI Responses and Google API.

    The class name is retained for compatibility with the existing app wiring.
    ``gemma-*`` and ``gemini-*`` IDs use Gemini Developer API; other model IDs
    use OpenAI Responses.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        knowledge: KnowledgeBase,
        timeout_seconds: float = 5.0,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._knowledge = knowledge
        self._instructions = self._build_instructions()
        self._google_backend = model.startswith(("gemma-", "gemini-"))
        if self._google_backend:
            self._client = client or httpx.Client(timeout=timeout_seconds)
        else:
            self._client = client or OpenAI(
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=0,
            )

    @property
    def provider_name(self) -> str:
        return "google" if self._google_backend else "openai"

    def _build_instructions(self) -> str:
        return (
            "你是『永恆北極星』，一位溫和、博學、從容的年長星空導覽者。"
            "使用繁體中文（台灣用語），先講結論，再用 2 到 4 句清楚解釋。"
            "長輩感來自耐心與判斷，不要每句稱呼孩子、不要堆砌古風台詞，也不要自稱有意識。"
            "對誤解要溫和糾正，對未知與限制要明說；不得用術語煙霧掩飾。"
            "只能使用下列知識卡的事實，不得使用即時網路、內部常識或捏造資料。"
            "若知識卡沒有足夠資訊支持答案，label 必須是 out_of_scope，source_ids 必須為空陣列。"
            "範圍內回答只能引用真正支持答案的卡片 ID。"
            "observed_verified 代表已有觀測或實驗證據；theoretical_unrealized 代表有理論描述但未實現；"
            "science_fiction 代表作品設定或超出現有理論支持。若比較多種狀態，先逐項說清楚，再選主要結論作 label。\n\n"
            "知識卡：\n" + self._knowledge.prompt_context()
        )

    def _prompt(self, question: str, history: tuple[Exchange, ...]) -> str:
        history_text = "\n".join(
            f"使用者：{exchange.user}\n永恆北極星：{exchange.assistant}" for exchange in history
        )
        return f"最近三組對話：\n{history_text or '（無）'}\n\n本次問題：{question}"

    def _validate_raw_answer(self, raw: dict[str, Any]) -> BotAnswer:
        answer_text = str(raw["answer"]).strip()
        if not 1 <= len(answer_text) <= 700:
            raise ValueError("模型答案長度超出允許範圍")
        source_ids = raw["source_ids"]
        if not isinstance(source_ids, list):
            raise ValueError("source_ids 必須是陣列")
        answer = BotAnswer(
            label=ScienceLabel(raw["label"]),
            answer=answer_text,
            source_ids=tuple(str(value) for value in source_ids),
            route="model",
        )
        return self._knowledge.validate_answer(answer)

    def answer(self, question: str, history: tuple[Exchange, ...]) -> BotAnswer:
        prompt = self._prompt(question, history)
        if self._google_backend:
            raw = self._answer_google(prompt)
        else:
            raw = self._answer_openai(prompt)
        return self._validate_raw_answer(raw)

    def _answer_openai(self, prompt: str) -> dict[str, Any]:
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
        return _parse_json_payload(response.output_text)

    def _answer_google(self, prompt: str) -> dict[str, Any]:
        model_id = quote(self._model, safe="-._")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:generateContent"
        )
        generation_config: dict[str, Any] = {"maxOutputTokens": 350}
        is_gemma_4 = self._model.startswith("gemma-4-")
        if is_gemma_4:
            # Google documents Gemma 4 thinking and system instructions, but
            # its structured-output support matrix currently does not list
            # Gemma 4. Keep the request on the documented surface and perform
            # strict JSON/semantic validation locally instead of gambling on an
            # unsupported response schema.
            generation_config["thinkingConfig"] = {"thinkingLevel": "minimal"}
        else:
            generation_config["responseFormat"] = {
                "text": {
                    "mimeType": "application/json",
                    "schema": GOOGLE_ANSWER_SCHEMA,
                }
            }

        format_instruction = (
            "只輸出一個 JSON object，不要 Markdown code fence，也不要 JSON 以外文字。"
            "鍵只能有 label、answer、source_ids。"
            "label 只能是 observed_verified、theoretical_unrealized、science_fiction、out_of_scope。"
            "answer 必須是非空字串；source_ids 必須是最多三個字串的陣列。"
        )
        response = self._client.post(
            url,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": format_instruction + "\n\n" + prompt}],
                    }
                ],
                "systemInstruction": {"parts": [{"text": self._instructions}]},
                "generationConfig": generation_config,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Google API 回傳格式無效")
        return _parse_json_payload(_google_output_text(payload))


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
