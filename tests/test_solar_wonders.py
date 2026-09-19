from collections import Counter

import pytest

from eternal_polaris.secret_migration import SecretMigrationError, import_openai_key


@pytest.mark.parametrize("card_id", [f"sw{i:03}" for i in range(1, 27)])
def test_wonder_card_and_aliases_are_reachable(knowledge, card_id):
    card = knowledge.by_id[card_id]
    for prompt in (card.canonical_question, *card.aliases):
        assert knowledge.match_question(prompt).id == card_id


def test_expansion_contract_and_unique_questions(quiz_bank):
    assert len({q.prompt for q in quiz_bank.questions}) == 300
    for prefix, count, vault, difficulties in (
        ("S", 80, "cosmos", {"easy": 42, "medium": 33, "hard": 5}),
        ("M", 45, "future", {"easy": 20, "medium": 20, "hard": 5}),
        ("A", 25, "cosmos", {"easy": 11, "medium": 11, "hard": 3}),
    ):
        rows = [q for q in quiz_bank.questions if q.id.startswith(prefix)]
        assert {q.id for q in rows} == {f"{prefix}{i:03}" for i in range(1, count + 1)}
        assert Counter(q.difficulty for q in rows) == difficulties
        assert all(q.vault == vault and q.source_url.startswith("https://") for q in rows)
        assert all(len(q.prompt) <= 75 and max(map(len, q.choices)) <= 40 for q in rows)


@pytest.mark.parametrize("card_id", [f"sw{i:03}" for i in range(27, 57)])
def test_second_wonder_expansion_is_reachable(knowledge, card_id):
    card = knowledge.by_id[card_id]
    for prompt in (card.canonical_question, *card.aliases):
        assert knowledge.match_question(prompt).id == card_id


def test_science_boundaries_and_calculation(knowledge, quiz_bank):
    assert "尚非" in "".join(knowledge.by_id["sw010"].facts)
    assert "尚未確認" in "".join(knowledge.by_id["sw016"].facts)
    assert "不是實際任務" in "".join(knowledge.by_id["sw022"].facts)
    assert round(4.24 * 299792.458 / 192, -1) == 6620
    assert quiz_bank.by_id["M005"].correct_text == "6年"
    assert quiz_bank.by_id["S049"].correct_text == "6600年"


def test_secret_import_preserves_other_settings(tmp_path):
    source, output = tmp_path / "source.txt", tmp_path / ".env"
    key = "sk-" + "test" * 10
    source.write_text(key, encoding="utf-8")
    before = "# local\nAI_PROVIDER=google\nOPENAI_API_KEY=old\nLINE_CHANNEL_SECRET=keep\n"
    output.write_text(before, encoding="utf-8")
    import_openai_key(source, output)
    assert output.read_text(encoding="utf-8") == before.replace("OPENAI_API_KEY=old", "OPENAI_API_KEY=" + key)
    assert source.read_text(encoding="utf-8") == key
    import_openai_key(source, output)
    assert output.read_text(encoding="utf-8").count("OPENAI_API_KEY=") == 1


def test_ambiguous_secret_does_not_change_env(tmp_path):
    source, output = tmp_path / "source.txt", tmp_path / ".env"
    source.write_text("sk-" + "a" * 30 + "\nsk-" + "b" * 30, encoding="utf-8")
    output.write_text("AI_PROVIDER=google\n", encoding="utf-8")
    with pytest.raises(SecretMigrationError):
        import_openai_key(source, output)
    assert output.read_text(encoding="utf-8") == "AI_PROVIDER=google\n"
