from __future__ import annotations

import json
from pathlib import Path

import pytest

from eternal_polaris.evaluation import (
    _file_sha256,
    _validate_resume_report,
    compute_metrics,
    load_questions,
    run_online,
)
from eternal_polaris.models import BotAnswer, ScienceLabel

ROOT = Path(__file__).resolve().parents[1]


def test_eval_dataset_shape():
    assert len(load_questions(ROOT / "data" / "eval_questions.csv")) == 30


def test_resume_report_requires_matching_input_hashes(tmp_path: Path):
    questions = tmp_path / "questions.csv"
    knowledge = tmp_path / "knowledge.json"
    questions.write_text("id,question\nq1,一\n", encoding="utf-8")
    knowledge.write_text('{"cards": []}', encoding="utf-8")
    report = {
        "model": "model-a",
        "provider": "google",
        "questions_sha256": _file_sha256(questions),
        "knowledge_sha256": _file_sha256(knowledge),
    }

    assert _validate_resume_report(
        report,
        model="model-a",
        provider="google",
        questions_sha256=_file_sha256(questions),
        knowledge_sha256=_file_sha256(knowledge),
    ) is report

    questions.write_text("id,question\nq1,已修改\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="評估題"):
        _validate_resume_report(
            report,
            model="model-a",
            provider="google",
            questions_sha256=_file_sha256(questions),
            knowledge_sha256=_file_sha256(knowledge),
        )


def test_metrics_perfect_predictions():
    rows = []
    for label, count in [
        ("observed_verified", 8),
        ("theoretical_unrealized", 8),
        ("science_fiction", 8),
        ("out_of_scope", 6),
    ]:
        rows.extend(
            {
                "expected_label": label,
                "predicted_label": label,
                "source_match": True,
                "latency_ms": 100,
            }
            for _ in range(count)
        )
    metrics = compute_metrics(rows)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["out_of_scope_refusal_rate"] == 1.0


def test_outside_matrix_prediction_counts_as_false_negative():
    rows = [
        {
            "expected_label": "observed_verified",
            "predicted_label": "out_of_scope",
            "source_match": False,
            "latency_ms": 100,
        }
    ]
    rows.extend(
        {
            "expected_label": label,
            "predicted_label": label,
            "source_match": True,
            "latency_ms": 100,
        }
        for label in ("theoretical_unrealized", "science_fiction")
    )
    metrics = compute_metrics(rows)
    assert metrics["per_class"]["observed_verified"]["recall"] == 0.0
    assert metrics["in_scope_predictions_outside_matrix"]["observed_verified"] == 1


def test_out_of_scope_rows_do_not_count_as_manual_fact_scores():
    rows = [
        {
            "expected_label": "observed_verified",
            "predicted_label": "observed_verified",
            "source_match": True,
            "latency_ms": 100,
            "manual_fact_score": "2",
        },
        {
            "expected_label": "out_of_scope",
            "predicted_label": "out_of_scope",
            "source_match": True,
            "latency_ms": 100,
            "manual_fact_score": "0",
        },
    ]

    assert compute_metrics(rows)["manual_fact_accuracy"] is None


def test_online_run_never_copies_reference_manual_score(monkeypatch, settings, knowledge):
    class StubAnswerService:
        def __init__(self, *_args, **_kwargs):
            pass

        def answer(self, question, _history):
            if question == "失敗題":
                raise TimeoutError("simulated timeout")
            return BotAnswer(
                ScienceLabel.OBSERVED_VERIFIED,
                "測試回答",
                ("ov001",),
            )

    monkeypatch.setattr("eternal_polaris.evaluation.OpenAIAnswerService", StubAnswerService)
    rows = [
        {
            "id": "ok",
            "question": "成功題",
            "expected_label": "observed_verified",
            "expected_source_id": "ov001",
            "manual_fact_score": "1",
        },
        {
            "id": "error",
            "question": "失敗題",
            "expected_label": "observed_verified",
            "expected_source_id": "ov001",
            "manual_fact_score": "1",
        },
    ]

    records = run_online(rows, settings, knowledge)

    assert [record["manual_fact_score"] for record in records] == [None, None]


def test_online_run_retries_invalid_json_once(monkeypatch, settings, knowledge):
    class StubAnswerService:
        calls = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def answer(self, _question, _history):
            self.__class__.calls += 1
            if self.calls == 1:
                raise json.JSONDecodeError("truncated", "{", 1)
            return BotAnswer(ScienceLabel.GENERAL, "簡短回答", ())

    monkeypatch.setattr("eternal_polaris.evaluation.OpenAIAnswerService", StubAnswerService)
    records = run_online(
        [{"id": "retry", "question": "Python 語法", "expected_label": "out_of_scope", "expected_source_id": ""}],
        settings,
        knowledge,
        max_attempts=2,
    )

    assert records[0]["error_category"] is None
    assert records[0]["attempts"] == 2


def test_online_run_applies_request_spacing(monkeypatch, settings, knowledge):
    sleeps = []

    class StubAnswerService:
        def __init__(self, *_args, **_kwargs):
            pass

        def answer(self, _question, _history):
            return BotAnswer(ScienceLabel.GENERAL, "簡短回答", ())

    monkeypatch.setattr("eternal_polaris.evaluation.OpenAIAnswerService", StubAnswerService)
    monkeypatch.setattr("eternal_polaris.evaluation.time.sleep", sleeps.append)
    run_online(
        [
            {"id": "one", "question": "一", "expected_label": "out_of_scope", "expected_source_id": ""},
            {"id": "two", "question": "二", "expected_label": "out_of_scope", "expected_source_id": ""},
        ],
        settings,
        knowledge,
        min_request_interval_seconds=2.1,
    )

    assert sleeps and sleeps[0] > 2.0


def test_rate_limit_retry_uses_sixty_second_backoff(monkeypatch, settings, knowledge):
    sleeps = []

    class StubAnswerService:
        calls = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def answer(self, _question, _history):
            self.__class__.calls += 1
            if self.calls == 1:
                request = __import__("httpx").Request("POST", "https://example.invalid")
                response = __import__("httpx").Response(429, request=request)
                raise __import__("httpx").HTTPStatusError("limited", request=request, response=response)
            return BotAnswer(ScienceLabel.GENERAL, "簡短回答", ())

    monkeypatch.setattr("eternal_polaris.evaluation.OpenAIAnswerService", StubAnswerService)
    monkeypatch.setattr("eternal_polaris.evaluation.time.sleep", sleeps.append)
    records = run_online(
        [{"id": "limited", "question": "一", "expected_label": "out_of_scope", "expected_source_id": ""}],
        settings,
        knowledge,
        min_request_interval_seconds=2.1,
        max_attempts=2,
    )

    assert records[0]["error_category"] is None
    assert any(delay >= 59.9 for delay in sleeps)
