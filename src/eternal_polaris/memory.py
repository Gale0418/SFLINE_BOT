from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from .models import Exchange


@dataclass(slots=True)
class _MemoryEntry:
    exchanges: deque[Exchange]
    touched_at: float


class ConversationMemory:
    def __init__(
        self,
        salt: str,
        max_exchanges: int = 3,
        ttl_seconds: int = 1800,
        max_users: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._salt = salt
        self._max_exchanges = max_exchanges
        self._ttl_seconds = ttl_seconds
        self._max_users = max_users
        self._clock = clock
        self._entries: dict[str, _MemoryEntry] = {}
        self._lock = threading.Lock()

    def key_for(self, user_id: str) -> str:
        return hashlib.sha256(f"{self._salt}:{user_id}".encode()).hexdigest()

    def get(self, user_id: str) -> tuple[Exchange, ...]:
        key = self.key_for(user_id)
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                return ()
            entry.touched_at = now
            return tuple(entry.exchanges)

    def add(self, user_id: str, user_text: str, assistant_text: str) -> None:
        key = self.key_for(user_id)
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                if len(self._entries) >= self._max_users:
                    oldest_key = min(self._entries, key=lambda item: self._entries[item].touched_at)
                    self._entries.pop(oldest_key, None)
                entry = _MemoryEntry(deque(maxlen=self._max_exchanges), now)
                self._entries[key] = entry
            entry.exchanges.append(Exchange(user=user_text, assistant=assistant_text))
            entry.touched_at = now

    def _purge_expired(self, now: float) -> None:
        expired = [
            key for key, entry in self._entries.items() if now - entry.touched_at > self._ttl_seconds
        ]
        for key in expired:
            self._entries.pop(key, None)


class EventDeduplicator:
    def __init__(
        self,
        ttl_seconds: int = 600,
        max_events: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_events = max_events
        self._clock = clock
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def first_seen(self, event_id: str) -> bool:
        if not event_id:
            return True
        now = self._clock()
        with self._lock:
            self._purge_expired(now)
            if event_id in self._seen:
                return False
            if len(self._seen) >= self._max_events:
                oldest = min(self._seen, key=self._seen.get)  # type: ignore[arg-type]
                self._seen.pop(oldest, None)
            self._seen[event_id] = now
            return True

    def forget(self, event_id: str) -> None:
        if not event_id:
            return
        with self._lock:
            self._seen.pop(event_id, None)

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, seen_at in self._seen.items() if now - seen_at > self._ttl_seconds]
        for key in expired:
            self._seen.pop(key, None)


class RequestRateLimiter:
    """Small in-process sliding-window guard for public free-form requests."""

    def __init__(
        self,
        *,
        salt: str,
        per_user_per_minute: int = 12,
        global_per_minute: int = 120,
        max_users: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if per_user_per_minute < 1 or global_per_minute < per_user_per_minute or max_users < 1:
            raise ValueError("速率限制必須為正數，且全域限制不得小於單一使用者限制")
        self._salt = salt
        self._per_user = per_user_per_minute
        self._global = global_per_minute
        self._max_users = max_users
        self._clock = clock
        self._users: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self, user_id: str) -> bool:
        now = self._clock()
        cutoff = now - 60.0
        key = hashlib.sha256(f"{self._salt}:{user_id}".encode()).hexdigest()
        with self._lock:
            while self._all and self._all[0] <= cutoff:
                self._all.popleft()
            bucket = self._users.get(key)
            if bucket is None:
                if len(self._users) >= self._max_users:
                    self._users.pop(next(iter(self._users)))
                bucket = deque()
                self._users[key] = bucket
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._per_user or len(self._all) >= self._global:
                return False
            bucket.append(now)
            self._all.append(now)
            return True
