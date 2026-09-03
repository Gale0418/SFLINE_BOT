from __future__ import annotations

import itertools
import logging
import threading
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Protocol


EventHandler = Callable[[Any], None]
EventKeyFunction = Callable[[Any], str]


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
            acquired = 0
            for _ in batch:
                if not self._slots.acquire(blocking=False):
                    for _ in range(acquired):
                        self._slots.release()
                    return False
                acquired += 1
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
        except Exception as exc:
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
            except BaseException as exc:
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
