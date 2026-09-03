from __future__ import annotations

import json
from types import SimpleNamespace

from eternal_polaris.answer_service import OpenAIAnswerService, render_answer
from eternal_polaris.models import ScienceLabel


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_text=json.dumps(self.payload, ensure_ascii=False))


def test_openai_uses_structured_output_and_store_false(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    responses = FakeResponses(
        {"label": card.label.value, "answer": "這是受知識庫約束的回答。", "source_ids": [card.id]}
    )
    client = SimpleNamespace(responses=responses)
    service = OpenAIAnswerService("key", "gpt-5.6-luna", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    assert answer.source_ids == (card.id,)
    assert responses.kwargs["store"] is False
    assert responses.kwargs["reasoning"] == {"effort": "none"}
    assert "temperature" not in responses.kwargs
    assert responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert "來源：" in render_answer(answer, knowledge)
