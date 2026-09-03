from __future__ import annotations

import pytest

from eternal_polaris.knowledge import KnowledgeError
from eternal_polaris.models import BotAnswer, ScienceLabel


def test_knowledge_has_expected_shape(knowledge):
    assert len(knowledge.cards) == 24
    assert len(knowledge.by_id) == 24


def test_answer_needs_at_least_one_source_matching_primary_label(knowledge):
    observed_id = next(card.id for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.SCIENCE_FICTION, "錯誤引用", (observed_id,)))


def test_comparison_answer_may_include_secondary_label_sources(knowledge):
    theoretical_id = next(
        card.id for card in knowledge.cards if card.label is ScienceLabel.THEORETICAL_UNREALIZED
    )
    fiction_id = next(card.id for card in knowledge.cards if card.label is ScienceLabel.SCIENCE_FICTION)
    answer = knowledge.validate_answer(
        BotAnswer(
            ScienceLabel.THEORETICAL_UNREALIZED,
            "理論模型與作品設定並不相同。",
            (theoretical_id, fiction_id),
        )
    )
    assert answer.source_ids == (theoretical_id, fiction_id)


def test_out_of_scope_cannot_have_source(knowledge):
    source_id = knowledge.cards[0].id
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.OUT_OF_SCOPE, "拒答", (source_id,)))


def test_answer_sources_cannot_repeat(knowledge):
    card = knowledge.cards[0]
    answer = BotAnswer(card.label, "測試回答", (card.id, card.id))
    with pytest.raises(KnowledgeError, match="不得重複"):
        knowledge.validate_answer(answer)


def test_conservative_matcher_accepts_exact_alias_but_rejects_operational_prompt(knowledge):
    card = knowledge.cards[0]
    assert knowledge.match_question(card.aliases[0]) is card
    assert knowledge.match_question("幫我寫一個黑洞遊戲程式") is None
    assert knowledge.match_question("黑洞") is None
