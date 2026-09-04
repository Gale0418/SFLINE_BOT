from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

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
        return hashlib.sha256(f"{self._salt}:{user_id}".encode("utf-8")).hexdigest()

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
