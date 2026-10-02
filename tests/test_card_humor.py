from eternal_polaris.answer_service import render_answer
from eternal_polaris.learning import LearningManager
from eternal_polaris.models import BotAnswer, ScienceLabel


def test_all_cards_have_fixed_distinct_humor(knowledge):
    assert len(knowledge.cards) == 1234
    jokes = [card.cold_joke for card in knowledge.cards]
    assert all(10 <= len(joke) <= 100 for joke in jokes)
    assert len(set(jokes)) == len(jokes)
    assert all("冷知識:" not in joke for joke in jokes)


def test_humor_is_rendered_only_for_cited_cards_and_not_model_evidence(knowledge):
    card = knowledge.by_id["sw165"]
    answer = BotAnswer(card.label, "\n".join(card.facts), (card.id,))
    text = render_answer(answer, knowledge)
    assert f"冷知識: {card.cold_joke}" in text
    assert knowledge.by_id["sw169"].cold_joke not in text
    assert card.cold_joke not in knowledge.prompt_context((card,))
    assert "冷知識:" not in render_answer(BotAnswer(ScienceLabel.CHAT, "你好", ()), knowledge)


def test_learning_lesson_shows_its_fixed_humor(tmp_path, knowledge, quiz_bank):
    manager = LearningManager(tmp_path / "learning.db", salt="secret", knowledge=knowledge, bank=quiz_bank)
    manager.handle("alice", "學習路線 cosmos")
    result = manager.handle("alice", "學習地圖")
    option = next(o for o in result[1] if o.label.startswith("1. "))
    text, _ = manager.handle("alice", option.data, postback=True)
    card_id = manager.routes["cosmos"][0][1][0][0]
    assert f"冷知識: {knowledge.by_id[card_id].cold_joke}" in text


def test_short_known_topics_and_transport_intent(knowledge):
    assert knowledge.match_question("曲速").id == "sw165"
    assert knowledge.context_cards_for_question("快子")[0].id == "sw169"
    assert knowledge.match_question("超光速移動的辦法").id == "sw165"
    assert knowledge.context_cards_for_question("啊") == ()


def test_every_card_label_can_show_its_fixed_joke_without_model_sources(knowledge):
    import pytest
    from eternal_polaris.knowledge import KnowledgeError

    for card in knowledge.cards:
        answer = BotAnswer(card.label, card.canonical_question, (card.id,), route="local")
        grounded = knowledge.ground_answer(answer)
        assert f"冷知識: {card.cold_joke}" in render_answer(grounded, knowledge)
    general = next(card for card in knowledge.cards if card.label is ScienceLabel.GENERAL)
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.GENERAL, "模型不應冒用來源", (general.id,)))
