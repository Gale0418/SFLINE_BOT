from __future__ import annotations

import sqlite3
import threading
import time

from linebot.v3.webhooks import Event

from eternal_polaris.dispatcher import DurableEventDispatcher, ThreadPoolEventDispatcher
from eternal_polaris.line_gateway import AmbiguousReplyError


def _line_event(event_id: str):
    return Event.from_dict({
        "type": "message",
        "mode": "active",
        "timestamp": 1,
        "source": {"type": "user", "userId": "U-test"},
        "webhookEventId": event_id,
        "deliveryContext": {"isRedelivery": False},
        "replyToken": f"reply-{event_id}",
        "message": {"id": f"m-{event_id}", "type": "text", "quoteToken": "q", "text": "hi"},
    })


def test_dispatcher_preserves_fifo_per_key_and_parallelizes_users():
    first_started = threading.Event()
    release_first = threading.Event()
    other_user_done = threading.Event()
    records: list[tuple[str, int]] = []
    lock = threading.Lock()

    def handler(event):
        user, value = event
        if user == "A" and value == 1:
            first_started.set()
            assert release_first.wait(2)
        with lock:
            records.append(event)
        if user == "B":
            other_user_done.set()

    dispatcher = ThreadPoolEventDispatcher(
        max_workers=2,
        queue_capacity=2,
        max_pending_per_key=2,
        key_fn=lambda event: event[0],
    )
    assert dispatcher.submit_many([("A", 1), ("A", 2), ("B", 1)], handler)
    assert first_started.wait(1)
    assert other_user_done.wait(1)
    release_first.set()
    dispatcher.shutdown(wait=True)

    a_values = [value for user, value in records if user == "A"]
    assert a_values == [1, 2]
    assert ("B", 1) in records


def test_batch_admission_is_atomic_when_capacity_is_insufficient():
    called = []
    dispatcher = ThreadPoolEventDispatcher(
        max_workers=1,
        queue_capacity=0,
        max_pending_per_key=2,
        key_fn=lambda event: str(event),
    )
    assert dispatcher.submit_many([1, 2], called.append) is False
    dispatcher.shutdown(wait=True)
    assert called == []


def test_closed_dispatcher_rejects_new_work():
    dispatcher = ThreadPoolEventDispatcher(max_workers=1, queue_capacity=0)
    dispatcher.shutdown(wait=True)
    assert dispatcher.submit_many([1], lambda event: None) is False


def test_durable_dispatcher_persists_deduplicates_and_completes(tmp_path):
    path = tmp_path / "webhooks.sqlite3"
    called: list[str] = []
    done = threading.Event()

    def handler(event):
        called.append(event.webhook_event_id)
        done.set()

    dispatcher = DurableEventDispatcher(path, max_workers=1, queue_capacity=1)
    dispatcher.start(handler)
    event = _line_event("evt-durable")
    assert dispatcher.submit_many((event,), handler)
    assert done.wait(2)
    assert dispatcher.submit_many((event,), handler)
    time.sleep(0.1)
    dispatcher.shutdown(wait=True)
    assert called == ["evt-durable"]

    replayed: list[str] = []
    restarted = DurableEventDispatcher(path, max_workers=1, queue_capacity=1)
    restarted.start(lambda item: replayed.append(item.webhook_event_id))
    time.sleep(0.1)
    restarted.shutdown(wait=True)
    assert replayed == []


def test_durable_dispatcher_retries_definite_failure_but_not_ambiguous_reply(tmp_path):
    attempts = 0
    succeeded = threading.Event()

    def flaky(event):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("definite pre-reply failure")
        succeeded.set()

    dispatcher = DurableEventDispatcher(tmp_path / "retry.sqlite3", max_workers=1)
    dispatcher.start(flaky)
    assert dispatcher.submit_many((_line_event("evt-retry"),), flaky)
    assert succeeded.wait(3)
    dispatcher.shutdown(wait=True)
    assert attempts == 3

    ambiguous_calls = 0
    failed = threading.Event()

    def ambiguous(event):
        nonlocal ambiguous_calls
        ambiguous_calls += 1
        failed.set()
        raise AmbiguousReplyError("unknown")

    no_retry = DurableEventDispatcher(tmp_path / "ambiguous.sqlite3", max_workers=1)
    no_retry.start(ambiguous)
    assert no_retry.submit_many((_line_event("evt-ambiguous"),), ambiguous)
    assert failed.wait(2)
    time.sleep(0.4)
    no_retry.shutdown(wait=True)
    assert ambiguous_calls == 1


def test_restart_quarantines_unknown_processing_job_without_replaying(tmp_path):
    path = tmp_path / "interrupted.sqlite3"
    first = DurableEventDispatcher(path, max_workers=1)
    first.shutdown(wait=True)
    payload = _line_event("evt-interrupted").to_json()
    now = time.time()
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES (?,?, 'processing',1,?,?)",
            ("evt-interrupted", payload, now, now),
        )

    calls: list[str] = []
    restarted = DurableEventDispatcher(path, max_workers=1)
    restarted.start(lambda event: calls.append(event.webhook_event_id))
    time.sleep(0.2)
    restarted.shutdown(wait=True)

    with sqlite3.connect(path) as db:
        state, stored_payload, error_type = db.execute(
            "SELECT state,payload,error_type FROM webhook_jobs_v1 WHERE event_id=?",
            ("evt-interrupted",),
        ).fetchone()
    assert calls == []
    assert (state, stored_payload, error_type) == (
        "failed",
        None,
        "ProcessInterruptedUnknown",
    )
