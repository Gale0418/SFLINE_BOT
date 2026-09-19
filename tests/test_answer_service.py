from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from eternal_polaris.answer_service import (
    HybridAnswerService,
    OpenAIAnswerService,
    render_answer,
)
from eternal_polaris.knowledge import KnowledgeError
from eternal_polaris.models import LABEL_TITLES, BotAnswer, Exchange, ScienceLabel


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


@pytest.mark.parametrize("followup", [False, True])
def test_comet_is_not_silently_replaced_with_telescope(knowledge, followup):
    client = FakeGoogleClient({"label": "general", "answer": "哈勃望遠鏡不會毀滅世界。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    original = "有人說哈勃彗星會毀滅世界"
    history = (Exchange(original, "哈勃望遠鏡不會毀滅世界。"),) if followup else ()
    answer = service.answer("那是哪一年的消息" if followup else original, history)
    assert answer.route == "subject_clarification"
    assert answer.label is ScienceLabel.UNCERTAIN
    assert "哪一顆彗星" in answer.answer


def test_explicit_telescope_question_is_not_blocked(knowledge):
    client = FakeGoogleClient({"label": "general", "answer": "哈勃望遠鏡是太空望遠鏡。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    assert service.answer("哈勃望遠鏡是什麼？", ()).route == "model"


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
    assert answer.route == "model_grounded"
    assert responses.kwargs["store"] is False
    assert responses.kwargs["reasoning"] == {"effort": "none"}
    assert "temperature" not in responses.kwargs
    assert responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert "來源：" in render_answer(answer, knowledge)


def test_gemma_4_31b_uses_documented_google_contract_without_schema_gamble(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "這是 Gemma 受知識庫約束的回答。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemma-4-31b-it", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())

    assert service.provider_name == "google"
    assert answer.source_ids == (card.id,)
    assert answer.route == "model_grounded"
    assert client.url.endswith("/models/gemma-4-31b-it:generateContent")
    assert client.headers["x-goog-api-key"] == "google-key"
    config = client.body["generationConfig"]
    assert config["thinkingConfig"] == {"thinkingLevel": "minimal"}
    assert "responseFormat" not in config
    assert "永恆北極星" in client.body["systemInstruction"]["parts"][0]["text"]
    prompt_text = client.body["contents"][0]["parts"][0]["text"]
    assert "只輸出一個 JSON object" in prompt_text
    assert client.response.raise_calls == 1


def test_gemini_google_backend_uses_structured_output(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "這是 Gemini 結構化回答。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemini-3.6-flash", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    assert answer.source_ids == (card.id,)
    config = client.body["generationConfig"]
    assert config["responseFormat"]["text"]["mimeType"] == "application/json"
    schema = config["responseFormat"]["text"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["source_ids"]["maxItems"] == 3
    assert "thinkingConfig" not in config


def test_google_response_ignores_thought_parts(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "可公開顯示的答案。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemma-4-31b-it", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    expected_facts = "\n".join("• " + fact.rstrip("。！？") + "。" for fact in card.facts)
    assert answer.answer == f"【{LABEL_TITLES[card.label]}｜{card.canonical_question}】\n{expected_facts}"
    assert "internal" not in answer.answer


def test_science_model_claim_is_replaced_by_cited_reviewed_facts(knowledge):
    card = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "這是一句沒有被來源支持的主張。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("google-key", "gemma-4-31b-it", knowledge, client=client)
    answer = service.answer(card.canonical_question, ())
    assert "沒有被來源支持" not in answer.answer
    assert all(fact.rstrip("。！？") in answer.answer for fact in card.facts)
    assert answer.route == "model_grounded"


def test_science_answer_marks_each_mixed_classification_source(knowledge):
    first = next(card for card in knowledge.cards if card.label is ScienceLabel.OBSERVED_VERIFIED)
    other = next(card for card in knowledge.cards if card.label is ScienceLabel.SCIENCE_FICTION)
    answer = knowledge.ground_answer(
        BotAnswer(first.label, "混合來源", (first.id, other.id))
    )
    assert f"【{LABEL_TITLES[first.label]}｜" in answer.answer
    assert f"【{LABEL_TITLES[other.label]}｜" in answer.answer


def test_hybrid_uses_local_card_for_exact_question(knowledge):
    card = knowledge.cards[0]
    fallback = RecordingProvider(BotAnswer(card.label, "不應呼叫", (card.id,)))
    service = HybridAnswerService(fallback, knowledge)
    answer = service.answer(card.canonical_question, ())
    assert answer.route == "local"
    assert answer.source_ids == (card.id,)
    assert fallback.calls == 0


def test_hybrid_does_not_steal_operational_prompt(knowledge):
    fallback_answer = BotAnswer(ScienceLabel.OUT_OF_SCOPE, "拒答", (), route="model")
    fallback = RecordingProvider(fallback_answer)
    service = HybridAnswerService(fallback, knowledge)
    answer = service.answer("幫我寫一個黑洞遊戲程式", ())
    assert answer is fallback_answer
    assert fallback.calls == 1


def test_chat_is_natural_text_and_receives_history(knowledge):
    client = FakeGoogleClient({"label": "chat", "answer": "考試讓你累壞了嗎？", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    history = (Exchange("我在準備考試", "辛苦了。"),)
    answer = service.answer("今天有點累", history)
    assert render_answer(answer, knowledge) == "考試讓你累壞了嗎？"
    assert "我在準備考試" in client.body["contents"][0]["parts"][0]["text"]


def test_model_prompt_uses_bounded_relevant_knowledge_context(knowledge):
    card = knowledge.cards[0]
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": "有來源的回答。", "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    service.answer(card.canonical_question, ())

    system_text = client.body["systemInstruction"]["parts"][0]["text"]
    prompt_text = client.body["contents"][0]["parts"][0]["text"]
    assert len(system_text) < 20_000
    assert len(prompt_text) < 20_000
    assert f"[{card.id}]" in prompt_text
    assert "只能引用下列 ID" in prompt_text


def test_model_cannot_cite_card_outside_retrieved_evidence(knowledge):
    first, unrelated = knowledge.cards[0], knowledge.cards[-1]
    client = FakeGoogleClient(
        {"label": unrelated.label.value, "answer": "錯誤引用。", "source_ids": [unrelated.id]}
    )
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    with pytest.raises(ValueError, match="未提供"):
        service.answer(first.canonical_question, ())


def test_google_contract_rejects_non_string_answer_and_source_ids(knowledge):
    card = knowledge.cards[0]
    client = FakeGoogleClient(
        {"label": card.label.value, "answer": ["bad"], "source_ids": [card.id]}
    )
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    with pytest.raises(TypeError, match="answer 必須是字串"):
        service.answer(card.canonical_question, ())


def test_provider_prompt_masks_common_sensitive_values(knowledge):
    client = FakeGoogleClient({"label": "chat", "answer": "已遮罩。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    service.answer("我的信箱是 me@example.com，手機 0912-345-678", ())
    prompt = client.body["contents"][0]["parts"][0]["text"]
    assert "me@example.com" not in prompt
    assert "0912-345-678" not in prompt
    assert "[電子郵件已遮罩]" in prompt
    assert "[電話已遮罩]" in prompt


def test_provider_prompt_masks_extended_identity_and_location_values(knowledge):
    client = FakeGoogleClient({"label": "chat", "answer": "已遮罩。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    service.answer(
        "我叫王小明，身分證 A123456789，生日 2001/02/03，住在臺北市中正區忠孝東路一段1號，信用卡卡號 4111 1111 1111 1111",
        (),
    )
    prompt = client.body["contents"][0]["parts"][0]["text"]
    assert "王小明" not in prompt
    assert "A123456789" not in prompt
    assert "2001/02/03" not in prompt
    assert "臺北市中正區忠孝東路一段1號" not in prompt
    assert "4111 1111 1111 1111" not in prompt
    assert "[姓名已遮罩]" in prompt
    assert "[身分證號已遮罩]" in prompt
    assert "[日期已遮罩]" in prompt
    assert "[地址已遮罩]" in prompt
    assert "[付款卡號已遮罩]" in prompt


@pytest.mark.parametrize(
    "question",
    [
        "臺北市立天文科學教育館在哪裡？",
        "臺北市看流星雨可以去哪裡？",
        "1969年7月20日發生了什麼太空事件？",
        "一光年約9460730472580800公尺，這是怎麼算的？",
    ],
)
def test_provider_prompt_preserves_public_places_historical_dates_and_science_numbers(
    knowledge, question
):
    client = FakeGoogleClient({"label": "chat", "answer": "正常。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    service.answer(question, ())
    prompt = client.body["contents"][0]["parts"][0]["text"]
    assert question in prompt


def test_chat_cannot_claim_science_sources(knowledge):
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.CHAT, "閒聊", (knowledge.cards[0].id,)))


def test_science_still_requires_sources(knowledge):
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel.OBSERVED_VERIFIED, "科學事實", ()))


def test_followup_is_not_stolen_by_local_matching(knowledge):
    fallback = RecordingProvider(BotAnswer(ScienceLabel.CHAT, "讓我們接著聊。", ()))
    service = HybridAnswerService(fallback, knowledge)
    answer = service.answer(knowledge.cards[0].canonical_question, (Exchange("我有點擔心", "怎麼了？"),))
    assert answer.route == "model"
    assert fallback.calls == 1


def test_followup_preserves_original_wording_and_marks_history_fallible(knowledge):
    client = FakeGoogleClient({"label": "uncertain", "answer": "先確認你指的是哪個天體。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    service.answer("那是哪一年？", (Exchange("哈勃彗星會毀滅世界", "哈勃望遠鏡不會毀滅地球"),))
    body = client.body
    prompt = body["contents"][0]["parts"][0]["text"]
    assert "哈勃彗星會毀滅世界" in prompt
    assert "助手舊回答可能有錯" in prompt
    instructions = body["systemInstruction"]["parts"][0]["text"]
    assert "物件類型、事件描述與年代也是線索" in instructions
    assert "使用者的糾正也不自動等於事實" in instructions


@pytest.mark.parametrize("label", ["general", "uncertain"])
def test_open_topic_answers_render_without_fake_sources(knowledge, label):
    client = FakeGoogleClient({"label": label, "answer": "這是一般知識或待確認的內容。", "source_ids": []})
    service = OpenAIAnswerService("test", "gemma-4-26b-a4b-it", knowledge, client=client)
    answer = service.answer("卡爾薩根是誰？", ())
    rendered = render_answer(answer, knowledge)
    assert "超出範圍" not in rendered
    assert "來源：" not in rendered
    assert ("不是很確定" in rendered) == (label == "uncertain")
    assert label in client.body["contents"][0]["parts"][0]["text"]
    with pytest.raises(KnowledgeError):
        knowledge.validate_answer(BotAnswer(ScienceLabel(label), "未查證的回答", (knowledge.cards[0].id,)))
