from __future__ import annotations

import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import pytest
from linebot.v3.webhooks import Event

from eternal_polaris.dispatcher import (
    DurableEventDispatcher,
    RetryablePreReplyError,
    ThreadPoolEventDispatcher,
    requeue_interrupted,
)
from eternal_polaris.line_gateway import AmbiguousReplyError


def _line_event(event_id: str, *, user_id: str = "U-test"):
    return Event.from_dict({
        "type": "message",
        "mode": "active",
        "timestamp": 1,
        "source": {"type": "user", "userId": user_id},
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


def test_durable_per_key_cap_allows_other_conversation_to_use_remaining_capacity(tmp_path):
    first_started = threading.Event()
    release_first = threading.Event()
    other_user_done = threading.Event()
    calls: list[str] = []

    def handler(event):
        event_id = event.webhook_event_id
        calls.append(event_id)
        if event_id == "evt-hot-1":
            first_started.set()
            assert release_first.wait(3)
        if event_id == "evt-other":
            other_user_done.set()

    dispatcher = DurableEventDispatcher(
        tmp_path / "per-key-admission.sqlite3",
        max_workers=1,
        queue_capacity=2,
        max_pending_per_key=100,
        max_persisted_jobs=3,
        max_persisted_per_key=2,
        key_fn=lambda event: event.source.user_id,
    )
    dispatcher.start(handler)
    try:
        assert dispatcher._max_persisted_per_key == 2
        hot_first = _line_event("evt-hot-1", user_id="U-hot")
        hot_second = _line_event("evt-hot-2", user_id="U-hot")
        hot_third = _line_event("evt-hot-3", user_id="U-hot")
        other = _line_event("evt-other", user_id="U-other")

        assert dispatcher.submit_many((hot_first,), handler)
        assert first_started.wait(1)
        assert dispatcher.submit_many((hot_second,), handler)
        # Redelivery is acknowledged without consuming another per-key slot.
        assert dispatcher.submit_many((hot_first,), handler)
        assert dispatcher.submit_many((hot_third,), handler) is False
        # The hot conversation cannot consume all three global slots.
        assert dispatcher.submit_many((other,), handler)
        release_first.set()
        assert other_user_done.wait(3)
        assert calls.count("evt-hot-1") == 1
        assert "evt-hot-2" in calls
        assert "evt-other" in calls
        with sqlite3.connect(dispatcher._path) as db:
            hot_terminal_key = db.execute(
                "SELECT conversation_key FROM webhook_jobs_v1 WHERE event_id='evt-hot-1'"
            ).fetchone()[0]
        assert hot_terminal_key is None
    finally:
        release_first.set()
        dispatcher.shutdown(wait=True)


def test_durable_per_key_batch_admission_is_atomic(tmp_path):
    first_started = threading.Event()
    release_first = threading.Event()
    handler = lambda event: (
        first_started.set() if event.webhook_event_id == "evt-atomic-a" else None,
        release_first.wait(3) if event.webhook_event_id == "evt-atomic-a" else None,
    )
    path = tmp_path / "per-key-atomic.sqlite3"
    dispatcher = DurableEventDispatcher(
        path,
        max_workers=1,
        queue_capacity=2,
        max_pending_per_key=10,
        max_persisted_jobs=4,
        max_persisted_per_key=2,
        key_fn=lambda event: event.source.user_id,
    )
    dispatcher.start(handler)
    try:
        assert dispatcher.submit_many((_line_event("evt-atomic-a", user_id="U-A"),), handler)
        assert first_started.wait(1)
        batch = (
            _line_event("evt-atomic-b", user_id="U-A"),
            _line_event("evt-atomic-c", user_id="U-A"),
        )
        assert dispatcher.submit_many(batch, handler) is False
        with sqlite3.connect(path) as db:
            assert db.execute(
                "SELECT event_id FROM webhook_jobs_v1 ORDER BY event_id"
            ).fetchall() == [("evt-atomic-a",)]
    finally:
        release_first.set()
        dispatcher.shutdown(wait=True)


def test_dispatcher_migrates_and_refreshes_active_conversation_keys(tmp_path):
    path = tmp_path / "legacy-key.sqlite3"
    payload = _line_event("evt-legacy-key", user_id="U-legacy").to_json()
    now = time.time()
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE webhook_jobs_v1 ("
            "event_id TEXT PRIMARY KEY,payload TEXT,state TEXT NOT NULL,"
            "attempts INTEGER NOT NULL DEFAULT 0,created_at REAL NOT NULL,"
            "updated_at REAL NOT NULL,error_type TEXT)"
        )
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES ('evt-legacy-key',?,'pending',0,?,?)",
            (payload, now, now),
        )

    dispatcher = DurableEventDispatcher(
        path,
        max_workers=1,
        max_persisted_per_key=2,
        key_fn=lambda event: f"rotated:{event.source.user_id}",
    )
    with sqlite3.connect(path) as db:
        key = db.execute(
            "SELECT conversation_key FROM webhook_jobs_v1 WHERE event_id='evt-legacy-key'"
        ).fetchone()[0]
        index_names = {
            row[1] for row in db.execute("PRAGMA index_list(webhook_jobs_v1)")
        }
    assert key == "rotated:U-legacy"
    assert "idx_webhook_jobs_v1_state_key" in index_names
    dispatcher.shutdown(wait=True)

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE webhook_jobs_v1 SET conversation_key='stale-key' "
            "WHERE event_id='evt-legacy-key'"
        )
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at,conversation_key) "
            "VALUES ('evt-invalid-key','{bad-json','pending',0,?,?, 'stale-invalid-key')",
            (now, now),
        )
    refreshed = DurableEventDispatcher(
        path,
        max_workers=1,
        max_persisted_per_key=2,
        key_fn=lambda event: f"rotated:{event.source.user_id}",
    )
    with sqlite3.connect(path) as db:
        keys = dict(
            db.execute(
                "SELECT event_id,conversation_key FROM webhook_jobs_v1 "
                "WHERE event_id IN ('evt-legacy-key','evt-invalid-key')"
            ).fetchall()
        )
    assert keys == {
        "evt-legacy-key": "rotated:U-legacy",
        "evt-invalid-key": None,
    }
    refreshed.shutdown(wait=True)


def test_durable_dispatcher_retries_definite_failure_but_not_ambiguous_reply(tmp_path):
    attempts = 0
    succeeded = threading.Event()

    def flaky(event):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RetryablePreReplyError("definite pre-reply failure")
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
    with sqlite3.connect(path) as db:
        state, stored_payload, error_type, conversation_key = db.execute(
            "SELECT state,payload,error_type,conversation_key "
            "FROM webhook_jobs_v1 WHERE event_id=?",
            ("evt-interrupted",),
        ).fetchone()
    assert calls == []
    assert (state, stored_payload, error_type) == (
        "interrupted",
        payload,
        "ProcessInterruptedUnknown",
    )
    assert conversation_key is None
    assert not restarted.ready()

    requeue_interrupted(path, "evt-interrupted")
    deadline = time.time() + 2
    while not calls and time.time() < deadline:
        time.sleep(0.02)
    assert calls == ["evt-interrupted"]
    deadline = time.time() + 2
    while not restarted.ready() and time.time() < deadline:
        time.sleep(0.02)
    assert restarted.ready()
    with pytest.raises(ValueError, match="not replayable"):
        requeue_interrupted(path, "evt-interrupted")
    restarted.shutdown(wait=True)


def test_requeue_interrupted_enforces_global_limit_atomically(tmp_path):
    path = tmp_path / "requeue-global.sqlite3"
    dispatcher = DurableEventDispatcher(path, max_workers=1)
    dispatcher.shutdown(wait=True)
    now = time.time()
    active_payload = _line_event("evt-active-global", user_id="U-active").to_json()
    interrupted_payload = _line_event("evt-replay-global", user_id="U-replay").to_json()
    with sqlite3.connect(path) as db:
        db.executemany(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES (?,?,?,0,?,?)",
            (
                ("evt-active-global", active_payload, "pending", now, now),
                ("evt-replay-global", interrupted_payload, "interrupted", now, now),
            ),
        )

    with pytest.raises(ValueError, match="global durable admission limit"):
        requeue_interrupted(path, "evt-replay-global", max_persisted_jobs=1)
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT state,conversation_key FROM webhook_jobs_v1 "
            "WHERE event_id='evt-replay-global'"
        ).fetchone()
    assert row == ("interrupted", None)


def test_requeue_interrupted_enforces_per_key_limit_atomically(tmp_path):
    path = tmp_path / "requeue-key.sqlite3"
    dispatcher = DurableEventDispatcher(path, max_workers=1)
    dispatcher.shutdown(wait=True)
    now = time.time()
    active = _line_event("evt-active-key", user_id="U-shared")
    interrupted = _line_event("evt-replay-key", user_id="U-shared")
    with sqlite3.connect(path) as db:
        db.executemany(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at,conversation_key) "
            "VALUES (?,?,?,0,?,?,?)",
            (
                (
                    active.webhook_event_id,
                    active.to_json(),
                    "pending",
                    now,
                    now,
                    "U-shared",
                ),
                (
                    interrupted.webhook_event_id,
                    interrupted.to_json(),
                    "interrupted",
                    now,
                    now,
                    None,
                ),
            ),
        )

    with pytest.raises(ValueError, match="conversation durable admission limit"):
        requeue_interrupted(
            path,
            interrupted.webhook_event_id,
            max_persisted_jobs=4,
            max_persisted_per_key=1,
            key_fn=lambda event: event.source.user_id,
        )
    with sqlite3.connect(path) as db:
        state, key = db.execute(
            "SELECT state,conversation_key FROM webhook_jobs_v1 WHERE event_id=?",
            (interrupted.webhook_event_id,),
        ).fetchone()
    assert (state, key) == ("interrupted", None)


def test_requeue_cli_restores_current_key_and_uses_app_admission_limits(
    monkeypatch, tmp_path, capsys
):
    from scripts import requeue_webhook
    from eternal_polaris.app import _event_key

    path = tmp_path / "requeue-cli-legacy.sqlite3"
    event = _line_event("evt-cli-requeue", user_id="U-cli")
    now = time.time()
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE webhook_jobs_v1 ("
            "event_id TEXT PRIMARY KEY,payload TEXT,state TEXT NOT NULL,"
            "attempts INTEGER NOT NULL DEFAULT 0,created_at REAL NOT NULL,"
            "updated_at REAL NOT NULL,error_type TEXT)"
        )
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES (?,?,'interrupted',1,?,?)",
            (event.webhook_event_id, event.to_json(), now, now),
        )
    synthetic_secret = "synthetic-cli-secret"
    monkeypatch.setattr(
        requeue_webhook,
        "Settings",
        SimpleNamespace(
            from_env=lambda: SimpleNamespace(
                webhook_worker_threads=1,
                webhook_queue_capacity=1,
                webhook_max_pending_per_key=0,
                line_channel_secret=synthetic_secret,
            )
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "requeue_webhook",
            "--db",
            str(path),
            "--event-id",
            event.webhook_event_id,
            "--confirm-event-id",
            event.webhook_event_id,
            "--accept-duplicate-reply-risk",
        ],
    )

    requeue_webhook.main()
    with sqlite3.connect(path) as db:
        state, key = db.execute(
            "SELECT state,conversation_key FROM webhook_jobs_v1 WHERE event_id=?",
            (event.webhook_event_id,),
        ).fetchone()
    output = capsys.readouterr().out
    assert (state, key) == (
        "pending",
        _event_key(event, synthetic_secret),
    )
    assert event.webhook_event_id in output
    assert synthetic_secret not in output
    assert "U-cli" not in key


def test_unknown_handler_failure_is_never_replayed(tmp_path):
    calls = 0
    failed = threading.Event()

    def unknown_phase(event):
        nonlocal calls
        calls += 1
        failed.set()
        raise RuntimeError("may have mutated state")

    dispatcher = DurableEventDispatcher(tmp_path / "unknown.sqlite3", max_workers=1)
    dispatcher.start(unknown_phase)
    assert dispatcher.submit_many((_line_event("evt-unknown"),), unknown_phase)
    assert failed.wait(2)
    time.sleep(0.4)
    dispatcher.shutdown(wait=True)
    assert calls == 1


def test_durable_dispatcher_skips_saturated_user_and_serves_another(tmp_path):
    first_started = threading.Event()
    release_first = threading.Event()
    other_user_done = threading.Event()
    calls: list[str] = []

    def handler(event):
        calls.append(event.webhook_event_id)
        if event.webhook_event_id == "evt-a1":
            first_started.set()
            assert release_first.wait(2)
        if event.webhook_event_id == "evt-b1":
            other_user_done.set()

    dispatcher = DurableEventDispatcher(
        tmp_path / "fair.sqlite3",
        max_workers=2,
        queue_capacity=2,
        max_pending_per_key=0,
        key_fn=lambda event: event.source.user_id,
    )
    dispatcher.start(handler)
    assert dispatcher.submit_many(
        (
            _line_event("evt-a1", user_id="U-A"),
            _line_event("evt-a2", user_id="U-A"),
            _line_event("evt-b1", user_id="U-B"),
        ),
        handler,
    )
    assert first_started.wait(1)
    assert other_user_done.wait(1)
    release_first.set()
    deadline = time.time() + 2
    while "evt-a2" not in calls and time.time() < deadline:
        time.sleep(0.02)
    dispatcher.shutdown(wait=True)
    assert calls.index("evt-b1") < calls.index("evt-a2")


def test_durable_pump_reuses_saturated_key_cache_and_serves_other_users(
    tmp_path, monkeypatch,
):
    path = tmp_path / "saturated-cache.sqlite3"
    first_started = threading.Event()
    release_first = threading.Event()
    other_user_done = threading.Event()
    all_done = threading.Event()
    calls: list[str] = []
    call_lock = threading.Lock()

    def handler(event):
        with call_lock:
            calls.append(event.webhook_event_id)
            if len(calls) == 21:
                all_done.set()
        if event.webhook_event_id == "evt-cache-a1":
            first_started.set()
            assert release_first.wait(3)
        if event.webhook_event_id == "evt-cache-b1":
            other_user_done.set()

    parse_count = 0
    original_from_json = Event.from_json

    def counted_from_json(payload):
        nonlocal parse_count
        parse_count += 1
        return original_from_json(payload)

    monkeypatch.setattr(Event, "from_json", staticmethod(counted_from_json))
    dispatcher = DurableEventDispatcher(
        path,
        max_workers=2,
        queue_capacity=0,
        max_pending_per_key=0,
        key_fn=lambda event: event.source.user_id,
    )
    dispatcher.start(handler)
    assert dispatcher.submit_many((_line_event("evt-cache-a1", user_id="U-A"),), handler)
    assert first_started.wait(1)
    assert dispatcher.submit_many(
        tuple(
            _line_event(f"evt-cache-a{i}", user_id="U-A")
            for i in range(2, 21)
        ),
        handler,
    )
    parses_after_initial_saturation = parse_count
    assert parses_after_initial_saturation == 20

    corrupt_at = time.time()
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES ('evt-cache-corrupt','{not-json','pending',0,?,?)",
            (corrupt_at, corrupt_at),
        )
    with dispatcher._state_lock:
        dispatcher._pump_locked()
    assert parse_count == parses_after_initial_saturation + 1
    with sqlite3.connect(path) as db:
        state, payload, error_type = db.execute(
            "SELECT state,payload,error_type FROM webhook_jobs_v1 "
            "WHERE event_id='evt-cache-corrupt'"
        ).fetchone()
    assert (state, payload) == ("failed", None)
    assert error_type

    assert dispatcher.submit_many((_line_event("evt-cache-b1", user_id="U-B"),), handler)
    assert other_user_done.wait(1)
    assert parse_count == parses_after_initial_saturation + 2
    with dispatcher._state_lock:
        dispatcher._pump_locked()
    assert parse_count == parses_after_initial_saturation + 2

    release_first.set()
    assert all_done.wait(5)
    dispatcher.shutdown(wait=True)
    assert len(calls) == 21
    assert calls.index("evt-cache-b1") < calls.index("evt-cache-a2")


def test_durable_store_indexes_match_queue_queries(tmp_path):
    path = tmp_path / "indexed.sqlite3"
    dispatcher = DurableEventDispatcher(path, max_workers=1)
    with sqlite3.connect(path) as db:
        delete_plan = db.execute(
            "EXPLAIN QUERY PLAN DELETE FROM webhook_jobs_v1 "
            "WHERE state IN ('done','failed','interrupted') AND updated_at < ?",
            (time.time(),),
        ).fetchall()
        interrupted_plan = db.execute(
            "EXPLAIN QUERY PLAN UPDATE webhook_jobs_v1 SET payload=NULL "
            "WHERE state='interrupted' AND updated_at < ?",
            (time.time(),),
        ).fetchall()
        count_plan = db.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM webhook_jobs_v1 "
            "WHERE state IN ('pending','queued','processing')"
        ).fetchall()
        pump_plan = db.execute(
            "EXPLAIN QUERY PLAN SELECT event_id,payload FROM webhook_jobs_v1 "
            "WHERE state='pending' ORDER BY created_at LIMIT ?",
            (1000,),
        ).fetchall()
        key_count_plan = db.execute(
            "EXPLAIN QUERY PLAN SELECT conversation_key,COUNT(*) "
            "FROM webhook_jobs_v1 "
            "WHERE state IN ('pending','queued','processing') "
            "GROUP BY conversation_key"
        ).fetchall()

    delete_text = " ".join(str(row[3]) for row in delete_plan)
    interrupted_text = " ".join(str(row[3]) for row in interrupted_plan)
    count_text = " ".join(str(row[3]) for row in count_plan)
    pump_text = " ".join(str(row[3]) for row in pump_plan)
    key_count_text = " ".join(str(row[3]) for row in key_count_plan)
    assert "idx_webhook_jobs_v1_state_updated" in delete_text
    assert "idx_webhook_jobs_v1_state_updated" in interrupted_text
    assert "USING COVERING INDEX idx_webhook_jobs_v1_state_" in count_text
    assert "idx_webhook_jobs_v1_state_created" in pump_text
    assert "idx_webhook_jobs_v1_state_key" in key_count_text
    dispatcher.shutdown(wait=True)


def test_durable_dispatcher_discards_expired_event_before_handler(tmp_path):
    path = tmp_path / "expired.sqlite3"
    dispatcher = DurableEventDispatcher(path, max_workers=1, retry_budget_seconds=45)
    payload = _line_event("evt-expired").to_json()
    old = time.time() - 600
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO webhook_jobs_v1 "
            "(event_id,payload,state,attempts,created_at,updated_at) "
            "VALUES (?,?, 'pending',0,?,?)",
            ("evt-expired", payload, old, old),
        )
    calls: list[str] = []
    dispatcher.start(lambda event: calls.append(event.webhook_event_id))
    deadline = time.time() + 2
    state = error_type = None
    while time.time() < deadline:
        with sqlite3.connect(path) as db:
            state, error_type, conversation_key = db.execute(
                "SELECT state,error_type,conversation_key FROM webhook_jobs_v1 WHERE event_id=?",
                ("evt-expired",),
            ).fetchone()
        if state == "failed":
            break
        time.sleep(0.02)
    dispatcher.shutdown(wait=True)
    assert calls == []
    assert (state, error_type, conversation_key) == (
        "failed", "ReplyTokenExpiredBeforeProcessing", None
    )
