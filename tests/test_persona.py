from __future__ import annotations

from eternal_polaris import persona


def test_persona_is_one_character_with_contextual_guardian_mode():
    assert "永恆北極星" in persona.WELCOME_TEXT
    assert "孩子" not in persona.HELP_TEXT
    assert "茶杯" in persona.CHALLENGE_INTRO_TEXT
    assert "寶庫不拒絕求知之人" in persona.CHALLENGE_INTRO_TEXT
    assert "不會被嘲笑" in persona.RULES_TEXT


def test_rendered_question_and_feedback_fit_line_text_limit():
    question = persona.render_question(
        vault_name="🌌 星海之庫",
        number=1,
        total=5,
        difficulty_name="守門人",
        question="哪個描述最準確？",
        choices=("選項一", "選項二", "選項三", "選項四"),
    )
    feedback = persona.render_feedback(
        correct=False,
        chosen_letter="A",
        correct_letter="B",
        correct_text="選項二",
        explanation="這是一段真正說明因果的科學解說。",
        source_name="NASA Science",
        score=0,
        answered=1,
        total=5,
    )
    final = persona.render_final(score=4, total=5, best_streak=3)
    assert "A. 選項一" in question
    assert "正確答案：B" in feedback
    assert "深空領航者" in final
    assert len(question + feedback + final) < 5000


def test_all_result_bands_have_a_non_shaming_title():
    texts = [persona.render_final(score=score, total=5, best_streak=score) for score in range(6)]
    assert all("最終得分" in text for text in texts)
    assert all("笨" not in text and "失敗者" not in text for text in texts)
