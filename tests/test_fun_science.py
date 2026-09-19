from collections import Counter

import pytest


@pytest.mark.parametrize("card_id", [f"ov{i:03}" for i in range(22, 34)])
def test_fun_card_questions_and_aliases_match(knowledge, card_id):
    card = knowledge.by_id[card_id]
    for text in (card.canonical_question, *card.aliases):
        assert knowledge.match_question(text).id == card_id


def test_fun_quiz_shape_and_sources(quiz_bank, knowledge):
    questions = [q for q in quiz_bank.questions if q.id.startswith("K")]
    assert {q.id for q in questions} == {f"K{i:03}" for i in range(1, 35)}
    assert Counter(q.difficulty for q in questions) == {"easy": 22, "medium": 12}
    assert len({q.prompt for q in quiz_bank.questions}) == 300
    for q in questions:
        card = knowledge.by_id[q.source_key.removeprefix("fun_")]
        assert q.source_url == card.source_url
        assert len(q.prompt) <= 70
        assert max(map(len, q.choices)) <= 40
        assert len(q.explanation) <= 100
    for vault in ("cosmos", "living_world", "laws", "future"):
        for difficulty in ("easy", "medium", "hard"):
            group = quiz_bank.select(vault=vault, difficulty=difficulty)
            counts = Counter(q.correct_letter for q in group)
            assert max(counts[x] for x in "ABCD") - min(counts[x] for x in "ABCD") <= 1


def test_misconception_answers_remain_correct_after_rebalancing(quiz_bank):
    expected = {"K003": "不能", "K004": "臭氧", "K005": "來源", "K021": "鳥類",
                "K025": "一天", "K026": "冰粒", "K032": "不能", "K033": "無線電"}
    # Stable IDs make wrong-answer shifts visible when answer positions rotate.
    for question_id, phrase in expected.items():
        assert phrase in quiz_bank.by_id[question_id].correct_text
