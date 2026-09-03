from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScienceLabel(StrEnum):
    OBSERVED_VERIFIED = "observed_verified"
    THEORETICAL_UNREALIZED = "theoretical_unrealized"
    SCIENCE_FICTION = "science_fiction"
    OUT_OF_SCOPE = "out_of_scope"


LABEL_TITLES = {
    ScienceLabel.OBSERVED_VERIFIED: "已觀測／已驗證",
    ScienceLabel.THEORETICAL_UNREALIZED: "理論上可行但尚未實現",
    ScienceLabel.SCIENCE_FICTION: "科幻設定",
    ScienceLabel.OUT_OF_SCOPE: "超出範圍",
}


@dataclass(frozen=True, slots=True)
class KnowledgeCard:
    id: str
    canonical_question: str
    aliases: tuple[str, ...]
    facts: tuple[str, ...]
    label: ScienceLabel
    source_name: str
    source_url: str


@dataclass(frozen=True, slots=True)
class BotAnswer:
    label: ScienceLabel
    answer: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Exchange:
    user: str
    assistant: str

