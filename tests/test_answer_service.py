from __future__ import annotations

import json
from types import SimpleNamespace

from eternal_polaris.answer_service import HybridAnswerService, OpenAIAnswerService, render_answer
from eternal_polaris.models import BotAnswer, ScienceLabel


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_text=json.dumps(self.payload, ensure_ascii=False))


class FakeGoogleResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.raise_calls = 0

    def raise_for_status(self):
        self.raise_calls += 1
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self.payload


class FakeGoogleClient:
    def __init__(self, answer_payload):
        text = json.dumps(answer_payload, ensure_ascii=False)
        self.response = FakeGoogleResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thought": True, "text": "internal"},
                                {"text": text},
                            ]
                        }
                    }
                ]
            }
        )
        self.url = None
        self.headers = None
        self.body = None

    def post(self, url, *, headers, json):
        self.url = url
        self.headers = headers
        self.body = json
        return self.response


class RecordingProvider:
    def __init__(self, answer):
        self.answer_value = answer
        self.calls = 0

    def answer(self, question, history):
        self.calls += 1
        return self.answer_value


def test_openai_uses_structured_output_and_store_false(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    responses = FakeResponses(
        {"label": card.label.value, "answer": "這是受知識庫約束的回答。", "source_ids": [card.id]}
    )
    client = SimpleNamespace(responses=responses)
    service = OpenAIAnswerService("key", "gpt-5.6-luna", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    assert service.provider_name == "openai"
    assert answer.source_ids == (card.id,)
    assert answer.route == "model"
    assert responses.kwargs["store"] is False
    assert responses.kwargs["reasoning"] == {"effort": "none"}
    assert "temperature" not in responses.kwargs
    assert responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert "來源：" in render_answer(answer, knowledge)


def test_gemma_4_31b_uses_google_free_api_contract(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "這是 Gemma 受知識庫約束的回答。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemma-4-31b-it", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())

    assert service.provider_name == "google"
    assert answer.source_ids == (card.id,)
    assert answer.route == "model"
    assert client.url.endswith("/models/gemma-4-31b-it:generateContent")
    assert client.headers["x-goog-api-key"] == "google-key"
    config = client.body["generationConfig"]
    assert config["thinkingConfig"] == {"thinkingLevel": "minimal"}
    assert config["responseFormat"]["text"]["mimeType"] == "application/json"
    schema = config["responseFormat"]["text"]["schema"]
    assert "maxLength" not in schema["properties"]["answer"]
    assert client.response.raise_calls == 1


def test_google_response_ignores_thought_parts(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "可公開顯示的答案。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemma-4-31b-it", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    assert answer.answer == "可公開顯示的答案。"
    assert "internal" not in answer.answer


def test_hybrid_uses_local_card_for_exact_question(knowledge):
    card = knowledge.cards[0]
    fallback = RecordingProvider(BotAnswer(card.label, "不應呼叫", (card.id,)))
    service = HybridAnswerService(fallback, knowledge)
    answer = service.answer(card.canonical_question, ())
    assert answer.route == "local"
    assert answer.source_ids == (card.id,)
    assert fallback.calls == 0


def test_hybrid_does_not_steal_operational_prompt(knowledge):
    card = knowledge.cards[0]
    fallback_answer = BotAnswer(ScienceLabel.OUT_OF_SCOPE, "拒答", (), route="model")
    fallback = RecordingProvider(fallback_answer)
    service = HybridAnswerService(fallback, knowledge)
    answer = service.answer("幫我寫一個黑洞遊戲程式", ())
    assert answer is fallback_answer
    assert fallback.calls == 1
