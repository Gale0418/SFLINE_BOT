from __future__ import annotations

import itertools
import json
import logging
import os
import sqlite3
import threading
import time
from collections import Counter, deque
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from linebot.v3.webhooks import Event

from .line_gateway import AmbiguousReplyError

EventHandler = Callable[[Any], None]
EventKeyFunction = Callable[[Any], str]


class RetryablePreReplyError(RuntimeError):
    """A proven pre-reply failure that is safe to execute again."""


class EventDispatcher(Protocol):
    def submit_many(self, events: Iterable[Any], handler: EventHandler) -> bool: ...
    def shutdown(self, *, wait: bool = True) -> None: ...


class InlineEventDispatcher:
    def submit_many(self, events: Iterable[Any], handler: EventHandler) -> bool:
        for event in events:
            handler(event)
        return True

    def shutdown(self, *, wait: bool = True) -> None:
        del wait


class ThreadPoolEventDispatcher:
    """Bounded worker pool with FIFO execution per conversation key."""

    def __init__(
        self,
        *,
        max_workers: int = 4,
        queue_capacity: int = 4,
        max_pending_per_key: int = 4,
        key_fn: EventKeyFunction | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        if queue_capacity < 0 or max_pending_per_key < 0:
            raise ValueError("queue limits cannot be negative")
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="line-webhook")
        self._slots = threading.BoundedSemaphore(max_workers + queue_capacity)
        self._max_outstanding_per_key = max_pending_per_key + 1
        self._state_lock = threading.Lock()
        self._pending: dict[str, deque[tuple[Any, EventHandler]]] = {}
        self._outstanding: dict[str, int] = {}
        self._active_keys: set[str] = set()
        self._anonymous_ids = itertools.count()
        self._closed = False
        self._key_fn = key_fn or (lambda event: "")
        self._logger = logger or logging.getLogger(__name__)

    def submit_many(self, events: Iterable[Any], handler: EventHandler) -> bool:
        batch = tuple(events)
        if not batch:
            return True
        with self._state_lock:
            if self._closed:
                return False
            keyed = tuple((event, self._safe_key(event)) for event in batch)
            additions = Counter(key for _, key in keyed)
            if any(
                self._outstanding.get(key, 0) + count > self._max_outstanding_per_key
                for key, count in additions.items()
            ):
                return False
            for acquired, _ in enumerate(batch):
                if not self._slots.acquire(blocking=False):
                    for _ in range(acquired):
                        self._slots.release()
                    return False
            new_keys: list[str] = []
            for event, key in keyed:
                self._pending.setdefault(key, deque()).append((event, handler))
                self._outstanding[key] = self._outstanding.get(key, 0) + 1
                if key not in self._active_keys:
                    self._active_keys.add(key)
                    new_keys.append(key)
            try:
                for key in new_keys:
                    self._executor.submit(self._run_key, key)
            except RuntimeError:
                for key, count in additions.items():
                    queue = self._pending[key]
                    for _ in range(count):
                        queue.pop()
                    if not queue:
                        self._pending.pop(key, None)
                        self._active_keys.discard(key)
                    remaining = self._outstanding[key] - count
                    if remaining:
                        self._outstanding[key] = remaining
                    else:
                        self._outstanding.pop(key, None)
                for _ in batch:
                    self._slots.release()
                return False
        return True

    def _safe_key(self, event: Any) -> str:
        try:
            key = str(self._key_fn(event) or "").strip()
        except Exception as exc:  # noqa: BLE001 - an injected key function cannot break admission
            self._logger.warning("event=worker_key_failed error_type=%s", type(exc).__name__)
            key = ""
        return key or f"anonymous:{next(self._anonymous_ids)}"

    def _run_key(self, key: str) -> None:
        while True:
            with self._state_lock:
                queue = self._pending.get(key)
                if not queue:
                    self._pending.pop(key, None)
                    self._active_keys.discard(key)
                    return
                event, handler = queue.popleft()
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - isolate one failed event from the worker
                self._logger.error("event=worker_failed error_type=%s", type(exc).__name__)
            finally:
                with self._state_lock:
                    remaining = self._outstanding[key] - 1
                    if remaining:
                        self._outstanding[key] = remaining
                    else:
                        self._outstanding.pop(key, None)
                self._slots.release()

    def shutdown(self, *, wait: bool = True) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)


@dataclass(frozen=True, slots=True)
class _DurableJob:
    event_id: str
    event: Any


class DurableEventDispatcher:
    """SQLite inbox plus bounded FIFO workers.

    An event is ACK-safe only after its JSON is committed. Definite processing
    failures receive bounded retries; ambiguous LINE reply failures are kept as
    failed records for diagnosis and are never blindly resent.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_workers: int = 4,
        queue_capacity: int = 4,
        max_pending_per_key: int = 4,
        max_persisted_jobs: int = 1000,
        max_attempts: int = 3,
        retry_budget_seconds: float = 45.0,
        dedupe_retention_seconds: int = 7 * 86_400,
        key_fn: EventKeyFunction | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if max_persisted_jobs < 1 or max_attempts < 1 or retry_budget_seconds <= 0:
            raise ValueError("durable dispatcher limits must be positive")
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_persisted_jobs = max_persisted_jobs
        self._max_attempts = max_attempts
        self._retry_budget_seconds = retry_budget_seconds
        self._dedupe_retention_seconds = dedupe_retention_seconds
        self._logger = logger or logging.getLogger(__name__)
        self._handler: EventHandler | None = None
        self._state_lock = threading.RLock()
        self._closed = False
        self._pump_error: str | None = None
        self._pump_wake = threading.Event()
        key_fn = key_fn or (lambda event: "")
        self._inner = ThreadPoolEventDispatcher(
            max_workers=max_workers,
            queue_capacity=queue_capacity,
            max_pending_per_key=max_pending_per_key,
            key_fn=lambda job: key_fn(job.event),
            logger=self._logger,
        )
        with closing(self._connect()) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS webhook_jobs_v1 (
                event_id TEXT PRIMARY KEY,
                payload TEXT,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                error_type TEXT
                )"""
            )
            db.execute(
                "UPDATE webhook_jobs_v1 SET state='pending',updated_at=? "
                "WHERE state='queued'",
                (time.time(),),
            )
            # A process can die after LINE accepted the reply but before we marked
            # the job done. Retrying that state could duplicate a one-time reply,
            # so quarantine it instead of guessing which side committed first.
            db.execute(
                "UPDATE webhook_jobs_v1 "
                "SET state='interrupted',updated_at=?,error_type='ProcessInterruptedUnknown' "
                "WHERE state='processing'",
                (time.time(),),
            )
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            self._logger.warning("event=webhook_store_permission_check_failed")
        self._pump_thread = threading.Thread(
            target=self._pump_loop, name="line-durable-pump", daemon=True
        )
        self._pump_thread.start()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def start(self, handler: EventHandler) -> None:
        with self._state_lock:
            if self._closed:
                raise RuntimeError("dispatcher is closed")
            if self._handler is not None and self._handler is not handler:
                raise RuntimeError("dispatcher handler cannot change")
            self._handler = handler
            self._pump_locked()

    def submit_many(self, events: Iterable[Any], handler: EventHandler) -> bool:
        batch = tuple(events)
        if not batch:
            return True
        unique_rows: dict[str, str] = {}
        for event in batch:
            payload = event.to_json() if hasattr(event, "to_json") else json.dumps(event.to_dict())
            event_id = str(getattr(event, "webhook_event_id", "") or "").strip()
            if not event_id:
                self._logger.error("event=webhook_rejected reason=missing_event_id")
                return False
            unique_rows[event_id] = payload
        rows = tuple(unique_rows.items())
        now = time.time()
        with self._state_lock:
            if self._closed:
                return False
            if self._handler is None:
                self._handler = handler
            elif self._handler is not handler:
                return False
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                cutoff = now - self._dedupe_retention_seconds
                db.execute(
                    "DELETE FROM webhook_jobs_v1 "
                    "WHERE state IN ('done','failed','interrupted') AND updated_at < ?",
                    (cutoff,),
                )
                db.execute(
                    "UPDATE webhook_jobs_v1 SET payload=NULL "
                    "WHERE state='interrupted' AND updated_at < ?",
                    (now - 3600,),
                )
                existing = {
                    event_id
                    for event_id, _ in rows
                    if db.execute(
                        "SELECT 1 FROM webhook_jobs_v1 WHERE event_id=?",
                        (event_id,),
                    ).fetchone()
                }
                new_rows = [row for row in rows if row[0] not in existing]
                active = db.execute(
                    "SELECT COUNT(*) FROM webhook_jobs_v1 WHERE state IN ('pending','queued','processing')"
                ).fetchone()[0]
                if active + len(new_rows) > self._max_persisted_jobs:
                    db.rollback()
                    return False
                db.executemany(
                    "INSERT INTO webhook_jobs_v1 "
                    "(event_id,payload,state,attempts,created_at,updated_at) "
                    "VALUES (?,?,'pending',0,?,?)",
                    ((event_id, payload, now, now) for event_id, payload in new_rows),
                )
                db.commit()
            self._pump_locked()
            self._pump_wake.set()
            return True

    def _pump_loop(self) -> None:
        while True:
            self._pump_wake.wait(0.2)
            self._pump_wake.clear()
            with self._state_lock:
                if self._closed:
                    return
                try:
                    self._pump_locked()
                    self._pump_error = None
                except Exception as exc:
                    self._pump_error = type(exc).__name__
                    self._logger.exception(
                        "event=durable_pump_failed error_type=%s", type(exc).__name__
                    )

    def _pump_locked(self) -> None:
        if self._handler is None or self._closed:
            return
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT event_id,payload FROM webhook_jobs_v1 "
                "WHERE state='pending' ORDER BY created_at LIMIT 128"
            ).fetchall()
        for event_id, payload in rows:
            try:
                event = Event.from_json(payload)
            except Exception as exc:  # noqa: BLE001 - corrupt durable payload must be quarantined
                self._set_failed(event_id, type(exc).__name__)
                continue
            with closing(self._connect()) as db:
                changed = db.execute(
                    "UPDATE webhook_jobs_v1 SET state='queued',updated_at=? "
                    "WHERE event_id=? AND state='pending'",
                    (time.time(), event_id),
                ).rowcount
            if not changed:
                continue
            job = _DurableJob(event_id, event)
            if not self._inner.submit_many((job,), self._run_job):
                with closing(self._connect()) as db:
                    db.execute(
                        "UPDATE webhook_jobs_v1 SET state='pending',updated_at=? WHERE event_id=?",
                        (time.time(), event_id),
                    )
                break

    def _run_job(self, job: _DurableJob) -> None:
        now = time.time()
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT attempts,created_at FROM webhook_jobs_v1 WHERE event_id=?",
                (job.event_id,),
            ).fetchone()
            if row is None:
                return
            attempts, created_at = int(row[0]) + 1, float(row[1])
            db.execute(
                "UPDATE webhook_jobs_v1 SET state='processing',attempts=?,updated_at=? WHERE event_id=?",
                (attempts, now, job.event_id),
            )
        try:
            handler = self._handler
            if handler is None:
                raise RuntimeError("durable dispatcher has no handler")
            handler(job.event)
        except AmbiguousReplyError as exc:
            self._set_failed(job.event_id, type(exc).__name__)
            self._logger.error("event=durable_job_failed reason=ambiguous_reply")
        except RetryablePreReplyError as exc:
            retry = attempts < self._max_attempts and now - created_at < self._retry_budget_seconds
            with closing(self._connect()) as db:
                db.execute(
                    "UPDATE webhook_jobs_v1 SET state=?,payload=CASE WHEN ? THEN payload ELSE NULL END,"
                    "updated_at=?,error_type=? WHERE event_id=?",
                    (
                        "pending" if retry else "failed",
                        retry,
                        time.time(),
                        type(exc).__name__,
                        job.event_id,
                    ),
                )
            self._logger.error(
                "event=durable_job_failed retry=%s error_type=%s", retry, type(exc).__name__
            )
        except Exception as exc:  # noqa: BLE001 - unknown phase must never replay side effects
            self._set_failed(job.event_id, type(exc).__name__)
            self._logger.error(
                "event=durable_job_failed retry=false reason=unknown_processing_phase "
                "error_type=%s",
                type(exc).__name__,
            )
        else:
            with closing(self._connect()) as db:
                db.execute(
                    "UPDATE webhook_jobs_v1 SET state='done',payload=NULL,updated_at=?,error_type=NULL "
                    "WHERE event_id=?",
                    (time.time(), job.event_id),
                )
        finally:
            self._pump_wake.set()

    def _set_failed(self, event_id: str, error_type: str) -> None:
        with closing(self._connect()) as db:
            db.execute(
                "UPDATE webhook_jobs_v1 SET state='failed',payload=NULL,updated_at=?,error_type=? "
                "WHERE event_id=?",
                (time.time(), error_type, event_id),
            )

    def ready(self) -> bool:
        try:
            with self._state_lock:
                if self._closed or not self._pump_thread.is_alive() or self._pump_error:
                    return False
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("SELECT 1 FROM webhook_jobs_v1 LIMIT 1").fetchone()
                interrupted = db.execute(
                    "SELECT COUNT(*) FROM webhook_jobs_v1 WHERE state='interrupted'"
                ).fetchone()[0]
                db.rollback()
            return interrupted == 0
        except sqlite3.Error:
            return False

    def shutdown(self, *, wait: bool = True) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._pump_wake.set()
        self._pump_thread.join(timeout=2)
        self._inner.shutdown(wait=wait)
