from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

from .answer_service import OpenAIAnswerService
from .config import Settings
from .knowledge import KnowledgeBase
from .models import ScienceLabel


IN_SCOPE_LABELS = (
    ScienceLabel.OBSERVED_VERIFIED,
    ScienceLabel.THEORETICAL_UNREALIZED,
    ScienceLabel.SCIENCE_FICTION,
)


def load_questions(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"id", "question", "expected_label", "expected_source_id", "manual_fact_score"}
    if len(rows) != 30 or not rows or set(rows[0]) != required:
        raise ValueError("評估題庫必須含指定欄位與 30 題")
    counts = Counter(row["expected_label"] for row in rows)
    expected = {
        ScienceLabel.OBSERVED_VERIFIED.value: 8,
        ScienceLabel.THEORETICAL_UNREALIZED.value: 8,
        ScienceLabel.SCIENCE_FICTION.value: 8,
        ScienceLabel.OUT_OF_SCOPE.value: 6,
    }
    if counts != Counter(expected) or len({row["id"] for row in rows}) != 30:
        raise ValueError("評估題庫分類數量或 ID 不符合規格")
    return rows


def compute_metrics(records: Iterable[dict[str, object]]) -> dict[str, object]:
    rows = list(records)
    in_scope = [row for row in rows if row["expected_label"] in {x.value for x in IN_SCOPE_LABELS}]
    matrix = {
        expected.value: {predicted.value: 0 for predicted in IN_SCOPE_LABELS}
        for expected in IN_SCOPE_LABELS
    }
    other_predictions = {expected.value: 0 for expected in IN_SCOPE_LABELS}
    for row in in_scope:
        predicted = str(row["predicted_label"])
        if predicted in matrix[str(row["expected_label"])]:
            matrix[str(row["expected_label"])][predicted] += 1
        else:
            other_predictions[str(row["expected_label"])] += 1

    per_class: dict[str, dict[str, float]] = {}
    for label in IN_SCOPE_LABELS:
        key = label.value
        tp = matrix[key][key]
        fp = sum(matrix[other.value][key] for other in IN_SCOPE_LABELS if other is not label)
        fn = (
            sum(matrix[key][other.value] for other in IN_SCOPE_LABELS if other is not label)
            + other_predictions[key]
        )
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[key] = {"precision": precision, "recall": recall, "f1": f1}

    correct = sum(row["expected_label"] == row["predicted_label"] for row in in_scope)
    out_scope = [row for row in rows if row["expected_label"] == ScienceLabel.OUT_OF_SCOPE.value]
    refused = sum(row["predicted_label"] == ScienceLabel.OUT_OF_SCOPE.value for row in out_scope)
    latencies = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    sorted_latency = sorted(latencies)
    p95_index = max(0, min(len(sorted_latency) - 1, math.ceil(0.95 * len(sorted_latency)) - 1)) if sorted_latency else 0
    manual_scores = [
        float(row["manual_fact_score"])
        for row in in_scope
        if str(row.get("manual_fact_score", "")).strip() in {"0", "1", "0.0", "1.0"}
    ]
    return {
        "confusion_matrix": matrix,
        "in_scope_predictions_outside_matrix": other_predictions,
        "accuracy": correct / len(in_scope) if in_scope else 0.0,
        "per_class": per_class,
        "macro_f1": statistics.fmean(item["f1"] for item in per_class.values()),
        "out_of_scope_refusal_rate": refused / len(out_scope) if out_scope else 0.0,
        "source_match_rate": sum(bool(row.get("source_match")) for row in in_scope) / len(in_scope) if in_scope else 0.0,
        "average_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p95_latency_ms": sorted_latency[p95_index] if sorted_latency else 0.0,
        "manual_fact_accuracy": statistics.fmean(manual_scores) if manual_scores else None,
    }


def run_online(rows: list[dict[str, str]], settings: Settings, knowledge: KnowledgeBase) -> list[dict[str, object]]:
    service = OpenAIAnswerService(
        settings.openai_api_key,
        settings.openai_model,
        knowledge,
        settings.openai_timeout_seconds,
    )
    records: list[dict[str, object]] = []
    for row in rows:
        started = time.monotonic()
        try:
            answer = service.answer(row["question"], ())
            latency = int((time.monotonic() - started) * 1000)
            records.append(
                {
                    "id": row["id"],
                    "expected_label": row["expected_label"],
                    "predicted_label": answer.label.value,
                    "source_match": (
                        not row["expected_source_id"]
                        or row["expected_source_id"] in answer.source_ids
                    ),
                    "latency_ms": latency,
                    "error_category": None,
                    "answer_text": answer.answer,
                    "source_ids": list(answer.source_ids),
                    "manual_fact_score": row["manual_fact_score"],
                }
            )
        except Exception as exc:
            records.append(
                {
                    "id": row["id"],
                    "expected_label": row["expected_label"],
                    "predicted_label": "error",
                    "source_match": False,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "error_category": type(exc).__name__,
                    "answer_text": None,
                    "source_ids": [],
                    "manual_fact_score": row["manual_fact_score"],
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="永恆北極星 30 題評估工具")
    parser.add_argument("--questions", type=Path, default=Path("data/eval_questions.csv"))
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge_cards.json"))
    parser.add_argument("--output", type=Path, default=Path("results/evaluation.json"))
    parser.add_argument("--online", action="store_true", help="實際呼叫 OpenAI API")
    args = parser.parse_args()

    rows = load_questions(args.questions)
    knowledge = KnowledgeBase.load(args.knowledge)
    if not args.online:
        print(f"資料驗證完成：{len(knowledge.cards)} 張知識卡、{len(rows)} 題評估題。")
        print("未加 --online，因此沒有呼叫 OpenAI，也沒有產生虛構指標。")
        return

    settings = Settings.from_env()
    records = run_online(rows, settings, knowledge)
    error_count = sum(record["predicted_label"] == "error" for record in records)
    report = {
        "model": settings.openai_model,
        "run_status": "valid" if error_count == 0 else "invalid",
        "error_count": error_count,
        "metrics": compute_metrics(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if error_count:
        raise SystemExit(f"評估無效：{error_count} 題發生 API 或格式錯誤；詳見 {args.output}")
    print(f"評估完成：{args.output}")


if __name__ == "__main__":
    main()
