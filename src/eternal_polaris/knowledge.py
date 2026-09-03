from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from .models import BotAnswer, KnowledgeCard, ScienceLabel


class KnowledgeError(ValueError):
    pass


class KnowledgeBase:
    def __init__(self, cards: list[KnowledgeCard]) -> None:
        self.cards = tuple(cards)
        self.by_id = {card.id: card for card in cards}
        if len(self.by_id) != len(cards):
            raise KnowledgeError("知識卡 ID 不可重複")

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

    def validate_answer(self, answer: BotAnswer) -> BotAnswer:
        if answer.label is ScienceLabel.OUT_OF_SCOPE:
            if answer.source_ids:
                raise KnowledgeError("超出範圍回答不得附來源")
            return answer
        if not answer.answer.strip() or not answer.source_ids:
            raise KnowledgeError("範圍內回答必須有內容與來源")
        if len(answer.source_ids) != len(set(answer.source_ids)):
            raise KnowledgeError("回答來源不得重複")
        for source_id in answer.source_ids:
            card = self.by_id.get(source_id)
            if card is None or card.label is not answer.label:
                raise KnowledgeError("回答來源不存在或與分類不一致")
        return answer

    def source_names(self, source_ids: tuple[str, ...]) -> list[str]:
        names: list[str] = []
        for source_id in source_ids:
            name = self.by_id[source_id].source_name
            if name not in names:
                names.append(name)
        return names
