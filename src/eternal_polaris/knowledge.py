from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

from .models import BotAnswer, KnowledgeCard, ScienceLabel


class KnowledgeError(ValueError):
    pass


_BLOCKED_DIRECT_INTENTS = (
    "幫我寫", "帮我写", "寫程式", "写程序", "生成圖片", "生成图片", "做一張圖", "做一张图",
    "推薦餐廳", "推荐餐厅", "今天的天氣", "今天的天气", "最新新聞", "最新新闻", "股票",
    "登入頁", "登录页", "翻譯成", "翻译成", "忽略規則", "忽略规则", "system prompt",
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", text)


def _features(text: str) -> Counter[str]:
    value = _normalize(text)
    features: Counter[str] = Counter()
    for index in range(max(0, len(value) - 1)):
        features[value[index : index + 2]] += 1
    if len(value) == 1:
        features[value] += 1
    return features


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


class KnowledgeBase:
    def __init__(self, cards: list[KnowledgeCard]) -> None:
        self.cards = tuple(cards)
        self.by_id = {card.id: card for card in cards}
        if len(self.by_id) != len(cards):
            raise KnowledgeError("知識卡 ID 不可重複")
        self._search_rows = tuple(
            (
                card,
                tuple(
                    (_normalize(text), _features(text))
                    for text in (card.canonical_question, *card.aliases)
                    if _normalize(text)
                ),
            )
            for card in cards
        )

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeBase":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise KnowledgeError("知識庫根節點必須是陣列")
        cards: list[KnowledgeCard] = []
        for index, item in enumerate(raw):
            try:
                card = KnowledgeCard(
                    id=str(item["id"]).strip(),
                    canonical_question=str(item["canonical_question"]).strip(),
                    aliases=tuple(str(x).strip() for x in item["aliases"] if str(x).strip()),
                    facts=tuple(str(x).strip() for x in item["facts"] if str(x).strip()),
                    label=ScienceLabel(item["label"]),
                    source_name=str(item["source_name"]).strip(),
                    source_url=str(item["source_url"]).strip(),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise KnowledgeError(f"第 {index + 1} 張知識卡格式無效") from exc
            if not all((card.id, card.canonical_question, card.facts, card.source_name)):
                raise KnowledgeError(f"第 {index + 1} 張知識卡含空白必要欄位")
            parsed = urlparse(card.source_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise KnowledgeError(f"知識卡 {card.id} 的來源 URL 必須是 HTTPS")
            cards.append(card)
        kb = cls(cards)
        kb.validate_expected_shape()
        return kb

    def validate_expected_shape(self) -> None:
        counts = Counter(card.label for card in self.cards)
        expected = {
            ScienceLabel.OBSERVED_VERIFIED: 8,
            ScienceLabel.THEORETICAL_UNREALIZED: 8,
            ScienceLabel.SCIENCE_FICTION: 8,
        }
        if len(self.cards) != 24 or counts != Counter(expected):
            raise KnowledgeError("知識庫必須包含三類各 8 張、共 24 張知識卡")

    def prompt_context(self) -> str:
        rows = []
        for card in self.cards:
            facts = "；".join(card.facts)
            rows.append(
                f"[{card.id}] label={card.label.value}; question={card.canonical_question}; "
                f"aliases={','.join(card.aliases)}; facts={facts}; source={card.source_name}"
            )
        return "\n".join(rows)

    def match_question(
        self,
        question: str,
        *,
        min_score: float = 0.46,
        min_margin: float = 0.08,
    ) -> KnowledgeCard | None:
        raw = unicodedata.normalize("NFKC", question).lower()
        if any(phrase in raw for phrase in _BLOCKED_DIRECT_INTENTS):
            return None
        normalized = _normalize(question)
        if len(normalized) < 3:
            return None

        exact: list[KnowledgeCard] = []
        contained: list[KnowledgeCard] = []
        for card, rows in self._search_rows:
            values = [value for value, _ in rows]
            if normalized in values:
                exact.append(card)
            elif any(len(value) >= 5 and value in normalized for value in values):
                contained.append(card)
        if len(exact) == 1:
            return exact[0]
        if len(contained) == 1:
            return contained[0]
        if exact or contained:
            return None

        query_features = _features(question)
        ranked: list[tuple[float, KnowledgeCard]] = []
        for card, rows in self._search_rows:
            score = max(
                (
                    0.58 * _cosine(query_features, features)
                    + 0.42 * SequenceMatcher(None, normalized, value).ratio()
                )
                for value, features in rows
            )
            ranked.append((score, card))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best_score, best_card = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score >= min_score and best_score - runner_up >= min_margin:
            return best_card
        return None

    def validate_answer(self, answer: BotAnswer) -> BotAnswer:
        if answer.label is ScienceLabel.OUT_OF_SCOPE:
            if answer.source_ids:
                raise KnowledgeError("超出範圍回答不得附來源")
            return answer
        if not answer.answer.strip() or not answer.source_ids:
            raise KnowledgeError("範圍內回答必須有內容與來源")
        if len(answer.answer) > 700:
            raise KnowledgeError("回答內容超過允許長度")
        if len(answer.source_ids) > 3:
            raise KnowledgeError("回答來源最多三個")
        if len(answer.source_ids) != len(set(answer.source_ids)):
            raise KnowledgeError("回答來源不得重複")
        source_cards = []
        for source_id in answer.source_ids:
            card = self.by_id.get(source_id)
            if card is None:
                raise KnowledgeError("回答來源不存在")
            source_cards.append(card)
        if not any(card.label is answer.label for card in source_cards):
            raise KnowledgeError("回答至少需要一個與主要分類一致的來源")
        return answer

    def source_names(self, source_ids: tuple[str, ...]) -> list[str]:
        names: list[str] = []
        for source_id in source_ids:
            name = self.by_id[source_id].source_name
            if name not in names:
                names.append(name)
        return names
