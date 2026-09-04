from __future__ import annotations

import threading

from eternal_polaris.dispatcher import ThreadPoolEventDispatcher


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
