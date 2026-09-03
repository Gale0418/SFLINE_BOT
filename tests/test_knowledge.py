from __future__ import annotations

import pytest

from eternal_polaris.knowledge import KnowledgeError
from eternal_polaris.models import BotAnswer, ScienceLabel


def test_knowledge_has_expected_shape(knowledge):
    assert len(knowledge.cards) == 24
    assert len(knowledge.by_id) == 24


def test_answer_source_label_must_match(knowledge):
    observed_id = next(card.id for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(
            BotAnswer(ScienceLabel.SCIENCE_FICTION, "錯誤引用", (observed_id,))
        )


def test_out_of_scope_cannot_have_source(knowledge):
    source_id = knowledge.cards[0].id
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.OUT_OF_SCOPE, "拒答", (source_id,)))


def test_answer_sources_cannot_repeat(knowledge):
    card = knowledge.cards[0]
    answer = BotAnswer(card.label, "測試回答", (card.id, card.id))

    with pytest.raises(KnowledgeError, match="不得重複"):
        knowledge.validate_answer(answer)
