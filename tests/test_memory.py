from __future__ import annotations

from eternal_polaris.memory import ConversationMemory, EventDeduplicator


def test_memory_keeps_last_three_and_expires():
    now = [100.0]
    memory = ConversationMemory("salt", ttl_seconds=30, clock=lambda: now[0])
    for number in range(4):
        memory.add("user-id", f"q{number}", f"a{number}")
    assert [item.user for item in memory.get("user-id")] == ["q1", "q2", "q3"]
    assert "user-id" not in memory.key_for("user-id")
    now[0] += 31
    assert memory.get("user-id") == ()


def test_deduplicator_accepts_again_after_ttl():
    now = [1.0]
    dedupe = EventDeduplicator(ttl_seconds=10, clock=lambda: now[0])
    assert dedupe.first_seen("event-1") is True
    assert dedupe.first_seen("event-1") is False
    now[0] += 11
    assert dedupe.first_seen("event-1") is True


def test_memory_purges_inactive_users_and_bounds_user_count():
    now = [0.0]
    memory = ConversationMemory("salt", ttl_seconds=10, max_users=2, clock=lambda: now[0])
    memory.add("u1", "q", "a")
    now[0] = 1
    memory.add("u2", "q", "a")
    now[0] = 2
    memory.add("u3", "q", "a")
    assert memory.get("u1") == ()
    assert len(memory.get("u2")) == 1
    now[0] = 20
    memory.add("u4", "q", "a")
    assert memory.get("u2") == ()
    assert memory.get("u3") == ()
