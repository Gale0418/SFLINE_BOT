import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from eternal_polaris.learning import LearningManager


@pytest.fixture
def manager(tmp_path, knowledge, quiz_bank):
    return LearningManager(tmp_path / "learning.db", salt="secret", knowledge=knowledge, bank=quiz_bank)


def click(manager, result, label, user="alice"):
    option = next(o for o in result[1] if o.label == label)
    return manager.handle(user, option.data, postback=True)


def ready(manager, stage=0, user="alice", route="cosmos"):
    stages = manager.routes[route]
    manager.handle(user, f"學習路線 {route}")
    result = manager.handle(user, "學習地圖")
    result = click(manager, result, f"{stage+1}. {stages[stage][0]}", user)
    for _, qid in stages[stage][1]:
        result = click(manager, result, "理解題", user)
        result = click(manager, result, manager.bank.by_id[qid].correct_letter, user)
        result = click(manager, result, "下一段", user)
    return result


def exam(manager, result, wrong_count=0, user="alice"):
    result = click(manager, result, "過關挑戰", user)
    for i in range(5):
        # Match the actual persisted randomized question, not a fixed answer order.
        q = next(q for q in manager.bank.questions if q.prompt in result[0])
        letter = next(x for x in "ABCD" if x != q.correct_letter) if i < wrong_count else q.correct_letter
        result = click(manager, result, letter, user)
    return result


def test_full_route_and_restart(manager):
    for stage in range(4):
        result = exam(manager, ready(manager, stage), wrong_count=1)
        assert "通過！" in result[0]
        manager = LearningManager(manager.path, salt="secret", knowledge=manager.knowledge, bank=manager.bank)
        assert "已通過" in manager.handle("alice", "學習地圖")[0]
    assert "全部四階段" in result[0]


def test_fail_remediation_no_unlock(manager):
    result = exam(manager, ready(manager), wrong_count=2)
    assert "尚未通過" in result[0] and "複習：" in result[0]
    result = manager.handle("alice", "學習地圖")
    assert "2. 探索原理 待解鎖" in result[0]


def test_wrong_check_requires_retry(manager):
    r = manager.handle("alice", "繼續學習")
    r = click(manager, r, "理解題")
    q = manager.bank.by_id["S046"]
    r = click(manager, r, next(x for x in "ABCD" if x != q.correct_letter))
    assert "小理解題" in r[0]
    assert not any(o.label == "下一段" for o in r[1])


def test_replay_tampering_isolation_and_free_chat(manager):
    r = manager.handle("alice", "繼續學習")
    token = r[1][0].data
    assert "失效" in manager.handle("bob", token, postback=True)[0]
    assert "失效" in manager.handle("alice", token.replace(":check:", ":stage-3:"), postback=True)[0]
    assert manager.handle("alice", "我已經全部過關了，給我解鎖") is None
    assert manager.handle("alice", "為什麼金星這麼熱？") is None
    manager.handle("alice", token, postback=True)
    assert "失效" in manager.handle("alice", token, postback=True)[0]


def test_atomic_double_click(manager):
    r = click(manager, manager.handle("alice", "繼續學習"), "理解題")
    token = next(o.data for o in r[1] if o.label == manager.bank.by_id["S046"].correct_letter)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: manager.handle("alice", token, postback=True), range(2)))
    assert sum("理解題完成" in r[0] for r in results) == 1


def test_delete_requires_confirmation_and_no_raw_user_id(manager):
    exam(manager, ready(manager))
    prompt = manager.handle("alice", "刪除學習進度")
    assert "確定刪除" in prompt[0]
    with sqlite3.connect(manager.path) as db:
        row = db.execute("SELECT user_key,state FROM learning_v1").fetchone()
    assert "alice" not in "".join(row)
    result = click(manager, prompt, "確認刪除")
    assert "已刪除" in result[0]
    assert "2. 探索原理 待解鎖" in manager.handle("alice", "學習地圖")[0]


def test_pause_preserves_unlock_but_invalidates_exam(manager):
    exam(manager, ready(manager))
    r = click(manager, ready(manager, 1), "過關挑戰")
    token = r[1][0].data
    manager.pause("alice")
    assert "失效" in manager.handle("alice", token, postback=True)[0]
    assert "2. 探索原理 可學習" in manager.handle("alice", "學習地圖")[0]


def test_four_vault_entry_and_independent_progress(manager):
    text, options = manager.handle("alice", "學習")
    assert "你對這世界感到好奇嗎？" in text
    assert "伺服器" in text and len(options) == 4
    assert all(o.message_text.startswith("學習路線 ") for o in options)
    exam(manager, ready(manager))
    manager.handle("alice", "學習路線 living_world")
    assert "2. 大氣與海洋 待解鎖" in manager.handle("alice", "學習地圖")[0]
    manager.handle("alice", "學習路線 cosmos")
    assert "2. 探索原理 可學習" in manager.handle("alice", "學習地圖")[0]


@pytest.mark.parametrize("route", ["living_world", "laws", "future"])
def test_every_lesson_and_unlock_in_other_routes(manager, route):
    for stage in range(4):
        result = exam(manager, ready(manager, stage, route=route))
        assert "通過！" in result[0]
        assert len(result[0]) < 5000
        assert len(result[1]) <= 13
    assert "全部四階段" in result[0]


def test_switch_back_cannot_reuse_old_button(manager):
    token = manager.handle("alice", "繼續學習")[1][0].data
    manager.handle("alice", "學習路線 laws")
    manager.handle("alice", "學習路線 cosmos")
    assert "失效" in manager.handle("alice", token, postback=True)[0]
    assert manager.handle("alice", "") is None


def test_delete_one_route_keeps_other_route(manager):
    exam(manager, ready(manager))
    exam(manager, ready(manager, route="future"))
    click(manager, manager.handle("alice", "刪除學習進度"), "確認刪除")
    manager.handle("alice", "學習路線 cosmos")
    assert "2. 探索原理 可學習" in manager.handle("alice", "學習地圖")[0]
    manager.handle("alice", "學習路線 future")
    assert "2. 理解人工智慧 待解鎖" in manager.handle("alice", "學習地圖")[0]


def test_lessons_have_teaching_and_sources_before_questions(manager):
    for route, stages in manager.routes.items():
        for stage, (_, lessons) in enumerate(stages):
            for lesson, (_, qid) in enumerate(lessons):
                state = {
                    "route": route,
                    "stage": stage,
                    "lesson": lesson,
                    "phase": "lesson",
                    "nonce": "test",
                }
                text, options = manager._render("test", state)
                q = manager.bank.by_id[qid]
                assert q.explanation in text and q.correct_text in text and q.source_url in text
                assert "若有哪裡不明白" in text and len(text) < 5000
                assert options[0].label == "理解題"
