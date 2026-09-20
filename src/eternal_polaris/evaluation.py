from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import time
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

import httpx

from .answer_service import OpenAIAnswerService
from .config import Settings
from .knowledge import KnowledgeBase, KnowledgeError
from .models import ScienceLabel

IN_SCOPE_LABELS = (
    ScienceLabel.OBSERVED_VERIFIED,
    ScienceLabel.THEORETICAL_UNREALIZED,
    ScienceLabel.SCIENCE_FICTION,
)
GOOGLE_MIN_REQUEST_INTERVAL_SECONDS = 2.1
DEFAULT_MAX_ATTEMPTS = 2
RATE_LIMIT_BACKOFF_SECONDS = 60.0


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_resume_report(
    previous: object,
    *,
    model: str,
    provider: str,
    questions_sha256: str,
    knowledge_sha256: str,
) -> dict[str, object]:
    if not isinstance(previous, dict):
        raise SystemExit("續跑報告格式無效")
    if previous.get("model") != model:
        raise SystemExit("續跑報告的 model 與目前設定不一致")
    if previous.get("provider") != provider:
        raise SystemExit("續跑報告的 provider 與目前設定不一致")
    if previous.get("questions_sha256") != questions_sha256:
        raise SystemExit("續跑報告的評估題與目前輸入不一致")
    if previous.get("knowledge_sha256") != knowledge_sha256:
        raise SystemExit("續跑報告的知識資料與目前輸入不一致")
    return previous


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


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(
        exc,
        (httpx.TimeoutException, TimeoutError, json.JSONDecodeError, KnowledgeError, TypeError, ValueError),
    )


def _safe_error_detail(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return "request timeout"
    return type(exc).__name__


def _retry_backoff_seconds(exc: Exception, min_request_interval_seconds: float) -> float:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        raw = exc.response.headers.get("retry-after", "").strip()
        try:
            retry_after = float(raw)
        except ValueError:
            retry_after = RATE_LIMIT_BACKOFF_SECONDS
        return max(min_request_interval_seconds, retry_after, RATE_LIMIT_BACKOFF_SECONDS)
    return min_request_interval_seconds


def run_online(
    rows: list[dict[str, str]],
    settings: Settings,
    knowledge: KnowledgeBase,
    *,
    min_request_interval_seconds: float = 0.0,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    progress_callback: Callable[[dict[str, object], int, int], None] | None = None,
) -> list[dict[str, object]]:
    if min_request_interval_seconds < 0:
        raise ValueError("min_request_interval_seconds 不可為負數")
    if not 1 <= max_attempts <= 3:
        raise ValueError("max_attempts 必須介於 1 與 3")
    service = OpenAIAnswerService(
        settings.openai_api_key,
        settings.openai_model,
        knowledge,
        settings.openai_timeout_seconds,
    )
    records: list[dict[str, object]] = []
    next_request_at = time.monotonic()
    for row in rows:
        delay = next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        started = time.monotonic()
        for attempt in range(1, max_attempts + 1):
            request_started = time.monotonic()
            next_request_at = request_started + min_request_interval_seconds
            try:
                answer = service.answer(row["question"], ())
                record = {
                    "id": row["id"],
                    "expected_label": row["expected_label"],
                    "predicted_label": answer.label.value,
                    "source_match": (
                        not row["expected_source_id"]
                        or row["expected_source_id"] in answer.source_ids
                    ),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "attempts": attempt,
                    "error_category": None,
                    "error_detail": None,
                    "answer_text": answer.answer,
                    "source_ids": list(answer.source_ids),
                    # A source-row score describes the reference question, not
                    # this newly generated answer. Human review must populate
                    # the result record after the online run.
                    "manual_fact_score": None,
                }
                records.append(record)
                if progress_callback is not None:
                    progress_callback(record, len(records), len(rows))
                break
            except Exception as exc:  # noqa: BLE001 - every failed sample belongs in the report
                if attempt >= max_attempts or not _is_retryable(exc):
                    record = {
                        "id": row["id"],
                        "expected_label": row["expected_label"],
                        "predicted_label": "error",
                        "source_match": False,
                        "latency_ms": int((time.monotonic() - started) * 1000),
                        "attempts": attempt,
                        "error_category": type(exc).__name__,
                        "error_detail": _safe_error_detail(exc),
                        "answer_text": None,
                        "source_ids": [],
                        "manual_fact_score": None,
                    }
                    records.append(record)
                    if progress_callback is not None:
                        progress_callback(record, len(records), len(rows))
                    break
                next_request_at = max(
                    next_request_at,
                    time.monotonic() + _retry_backoff_seconds(exc, min_request_interval_seconds),
                )
                delay = next_request_at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="永恆北極星 30 題評估工具")
    parser.add_argument("--questions", type=Path, default=Path("data/eval_questions.csv"))
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge_cards.json"))
    parser.add_argument("--output", type=Path, default=Path("results/evaluation.json"))
    parser.add_argument("--online", action="store_true", help="實際呼叫 OpenAI API")
    parser.add_argument(
        "--min-request-interval-seconds",
        type=float,
        default=None,
        help="模型請求起點的最小間隔；Google 預設 2.1 秒以低於每分鐘 30 次限制",
    )
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument(
        "--resume-from",
        type=Path,
        help="沿用同 provider／model 舊報告中的成功記錄，只重試失敗題",
    )
    args = parser.parse_args()

    rows = load_questions(args.questions)
    knowledge = KnowledgeBase.load(args.knowledge)
    questions_sha256 = _file_sha256(args.questions)
    knowledge_sha256 = _file_sha256(args.knowledge)
    if not args.online:
        print(f"資料驗證完成：{len(knowledge.cards)} 張知識卡、{len(rows)} 題評估題。")
        print("未加 --online，因此沒有呼叫 OpenAI，也沒有產生虛構指標。")
        return

    settings = Settings.from_env()
    min_interval = args.min_request_interval_seconds
    if min_interval is None:
        min_interval = GOOGLE_MIN_REQUEST_INTERVAL_SECONDS if settings.ai_provider == "google" else 0.0
    reused_by_id: dict[str, dict[str, object]] = {}
    if args.resume_from is not None:
        previous = _validate_resume_report(
            json.loads(args.resume_from.read_text(encoding="utf-8")),
            model=settings.openai_model,
            provider=settings.ai_provider,
            questions_sha256=questions_sha256,
            knowledge_sha256=knowledge_sha256,
        )
        valid_ids = {row["id"] for row in rows}
        reused_by_id = {
            str(record["id"]): record
            for record in previous.get("records", [])
            if str(record.get("id", "")) in valid_ids and not record.get("error_category")
        }

    pending_rows = [row for row in rows if row["id"] not in reused_by_id]
    reused_count = len(reused_by_id)

    def show_progress(record: dict[str, object], completed: int, pending_total: int) -> None:
        state = record.get("error_category") or record.get("predicted_label")
        print(
            f"[{reused_count + completed}/{reused_count + pending_total}] "
            f"{record['id']} attempts={record.get('attempts')} result={state}",
            flush=True,
        )

    new_records = run_online(
        pending_rows,
        settings,
        knowledge,
        min_request_interval_seconds=min_interval,
        max_attempts=args.max_attempts,
        progress_callback=show_progress,
    )
    records_by_id = {**reused_by_id, **{str(record["id"]): record for record in new_records}}
    records = [records_by_id[row["id"]] for row in rows]
    error_count = sum(record["predicted_label"] == "error" for record in records)
    report = {
        "model": settings.openai_model,
        "provider": settings.ai_provider,
        "questions_sha256": questions_sha256,
        "knowledge_sha256": knowledge_sha256,
        "min_request_interval_seconds": min_interval,
        "max_attempts": args.max_attempts,
        "resumed_from": str(args.resume_from) if args.resume_from is not None else None,
        "reused_record_count": reused_count,
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
