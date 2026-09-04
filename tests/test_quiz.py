from __future__ import annotations

import random

import pytest

from eternal_polaris.quiz import (
    DIFFICULTY_NAMES,
    LETTERS,
    VAULTS,
    QuizError,
    QuizManager,
    answer_postback_data,
)


def test_bank_has_balanced_96_question_shape(quiz_bank):
    assert len(quiz_bank.questions) == 96
    assert len({question.topic for question in quiz_bank.questions}) == 16
    assert all(question.source_url.startswith("https://") for question in quiz_bank.questions)
    for vault in set(VAULTS) - {"all"}:
        assert sum(question.vault == vault for question in quiz_bank.questions) == 24
        for difficulty in set(DIFFICULTY_NAMES) - {"mixed"}:
            rows = [
                question
                for question in quiz_bank.questions
                if question.vault == vault and question.difficulty == difficulty
            ]
            assert len(rows) == 8
            assert {letter: sum(question.correct_letter == letter for question in rows) for letter in LETTERS} == {
                "A": 2,
                "B": 2,
                "C": 2,
                "D": 2,
            }


def test_all_twenty_vault_difficulty_combinations_can_finish(quiz_bank):
    for vault_index, vault in enumerate(VAULTS):
        for difficulty_index, difficulty in enumerate(DIFFICULTY_NAMES):
            user_id = f"user-{vault}-{difficulty}"
            manager = QuizManager(
                quiz_bank,
                salt="secret",
                random_source=random.Random(vault_index * 10 + difficulty_index),
            )
            session = manager.start(user_id, vault=vault, difficulty=difficulty)
            assert len(session.questions) == 5
            assert len({question.id for question in session.questions}) == 5
            for _ in range(5):
                current = manager.current(user_id)
                assert current is not None
                letter = current.current_question.correct_letter
                token = answer_postback_data(manager, user_id, current, letter)
                outcome = manager.submit_postback(user_id, token)
            assert outcome.completed is True
            assert outcome.score == 5
            assert manager.current(user_id) is None


def test_signed_answer_is_bound_to_user_session_question_and_choice(quiz_bank):
    manager = QuizManager(quiz_bank, salt="secret", random_source=random.Random(1))
    alice = manager.start("alice", vault="cosmos", difficulty="easy")
    manager.start("bob", vault="cosmos", difficulty="easy")
    token = answer_postback_data(manager, "alice", alice, "A")

    with pytest.raises(QuizError):
        manager.submit_postback("bob", token)

    tampered = token.replace(":A:", ":B:")
    with pytest.raises(QuizError):
        manager.submit_postback("alice", tampered)


def test_old_answer_token_cannot_be_replayed(quiz_bank):
    manager = QuizManager(quiz_bank, salt="secret", random_source=random.Random(2))
    session = manager.start("alice", vault="living_world", difficulty="medium")
    token = answer_postback_data(manager, "alice", session, "A")
    manager.submit_postback("alice", token)
    with pytest.raises(QuizError):
        manager.submit_postback("alice", token)


def test_typed_answer_and_score_tracking(quiz_bank):
    manager = QuizManager(quiz_bank, salt="secret", random_source=random.Random(3))
    session = manager.start("alice", vault="laws", difficulty="hard")
    correct = session.current_question.correct_letter
    outcome = manager.submit_text("alice", correct)
    assert outcome.correct is True
    assert outcome.score == 1
    assert outcome.answered == 1
    assert outcome.best_streak == 1


def test_session_expires_without_exposing_raw_user_id(quiz_bank):
    now = [0.0]
    manager = QuizManager(
        quiz_bank,
        salt="secret",
        ttl_seconds=10,
        clock=lambda: now[0],
        random_source=random.Random(4),
    )
    manager.start("U-private", vault="future", difficulty="mixed")
    assert "U-private" not in manager._sessions
    now[0] = 11.0
    assert manager.current("U-private") is None
