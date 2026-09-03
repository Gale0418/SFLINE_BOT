from __future__ import annotations

from pathlib import Path

from eternal_polaris.evaluation import compute_metrics, load_questions


ROOT = Path(__file__).resolve().parents[1]


def test_eval_dataset_shape():
    assert len(load_questions(ROOT / "data" / "eval_questions.csv")) == 30


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
