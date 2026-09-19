"""Deterministic guided lessons; SQLite owns progress, never model output."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

from .commands import normalize_command
from .line_gateway import QuickReplyOption
from .quiz import VAULTS


# Each checkpoint explicitly names its prerequisite card. Reuse reviewed
# content instead of maintaining another competing factual answer database.
STAGES = (
    ("認識行星", (("sw020", "S046"), ("sw001", "S001"), ("sw002", "S004"), ("sw004", "S010"), ("sw007", "S019"))),
    ("探索原理", (("sw009", "S025"), ("sw010", "S028"), ("sw011", "S030"), ("sw019", "S044"), ("sw019", "S045"))),
    ("辨認證據", (("sw012", "S032"), ("sw012", "S033"), ("sw016", "S040"), ("sw017", "S043"), ("sw018", "S036"))),
    ("星際與電影", (("sw022", "S048"), ("sw023", "S049"), ("sw026", "M005"), ("sw025", "M011"), ("sw025", "M014"))),
)
LEARN_COMMANDS = {"學習", "開始學習", "繼續學習", "學習進度", "學習地圖", "暫停學習", "刪除學習進度"}
ROUTE_COMMANDS = {f"學習路線{key}": key for key in ("cosmos", "living_world", "laws", "future")}

# Explicit, stable question references: editing bank order must not change a course.
OTHER_ROUTES = {
    "living_world": (("腳下的地球", "L", (1, 2, 3, 4, 5)), ("大氣與海洋", "L", (7, 9, 8, 11, 12)), ("生命如何延續", "L", (13, 15, 16, 14, 17)), ("認識自己的身體", "L", (19, 20, 21, 22, 24))),
    "laws": (("力與運動", "P", (1, 2, 3, 4, 5)), ("時空與重力", "P", (8, 7, 9, 11, 12)), ("微觀世界", "P", (13, 14, 15, 16, 18)), ("材料的秘密", "P", (19, 20, 21, 22, 23))),
    "future": (("能源從哪裡來", "F", (1, 3, 4, 5, 6)), ("理解人工智慧", "F", (7, 8, 9, 12, 11)), ("走向太空", "F", (13, 14, 15, 16, 18)), ("想像與證據", "F", (19, 20, 21, 22, 23))),
}


class LearningManager:
    def __init__(self, path: Path, *, salt: str, knowledge, bank):
        self.path, self.salt, self.knowledge, self.bank = Path(path), salt.encode(), knowledge, bank
        self.routes = {"cosmos": STAGES}
        for route, stages in OTHER_ROUTES.items():
            self.routes[route] = tuple((title, tuple((None, f"{prefix}{n:03d}") for n in numbers)) for title, prefix, numbers in stages)
        for stages in self.routes.values():
            for _, lessons in stages:
                for card, question in lessons:
                    if (card is not None and card not in knowledge.by_id) or question not in bank.by_id:
                        raise ValueError("學習路線引用不存在的內容")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS learning_v1 (user_key TEXT PRIMARY KEY, state TEXT NOT NULL)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    def _key(self, user):
        return hmac.new(self.salt, user.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _new():
        return dict(unlocked=0, stage=0, lesson=0, phase="paused", nonce=secrets.token_hex(8), best={}, score=0, index=0, wrong=[])

    def _sign(self, key, nonce, action):
        return hmac.new(self.salt, f"{key}:{nonce}:{action}".encode(), hashlib.sha256).hexdigest()[:24]

    def _button(self, key, s, label, action):
        payload = f"learn:{s['nonce']}:{action}:{self._sign(key, s['nonce'], action)}"
        return QuickReplyOption(label, data=payload, display_text=label)

    def pause(self, user):
        self.handle(user, "暫停學習")

    def handle(self, user, text, *, postback=False):
        """Return None for ordinary chat. Every mutation is one transaction."""
        command = normalize_command(text)
        if not postback and command not in LEARN_COMMANDS and command not in ROUTE_COMMANDS and command.upper() not in tuple("ABCD"):
            return None
        key = self._key(user)
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM learning_v1 WHERE user_key=?", (key,)).fetchone()
            saved = json.loads(row[0]) if row else {"active": "cosmos", "routes": {}}
            # Preserve the initial single-route prototype if it has saved progress.
            if "routes" not in saved:
                saved = {"active": "cosmos", "routes": {"cosmos": saved}}
            if not postback and command in ("學習", "開始學習"):
                active = saved["routes"].get(saved["active"])
                if active:
                    active["nonce"] = secrets.token_hex(8)
                self._save(db, key, saved)
                return self._route_menu()
            if not postback and command in ROUTE_COMMANDS:
                active = saved["routes"].get(saved["active"])
                if active:
                    active["nonce"] = secrets.token_hex(8)
                saved["active"] = ROUTE_COMMANDS[command]
            route = saved["active"]
            s = saved["routes"].setdefault(route, self._new())
            s["route"] = route
            stages = self.routes[route]
            signing_key = f"{key}:{route}"
            if postback:
                parts = text.split(":")
                if len(parts) != 4 or parts[0] != "learn":
                    return "學習按鈕格式無效。請輸入「繼續學習」。", ()
                _, nonce, action, signature = parts
                if nonce != s["nonce"] or not hmac.compare_digest(signature, self._sign(signing_key, nonce, action)):
                    return "這個學習按鈕已失效或不屬於你。請輸入「繼續學習」。", ()
            else:
                action = {"學習":"resume", "開始學習":"resume", "繼續學習":"resume", "學習進度":"map", "學習地圖":"map", "暫停學習":"pause", "刪除學習進度":"delete_prompt"}.get(command, command.upper())
                if command in ROUTE_COMMANDS:
                    action = "map"
                if action in "ABCD" and (len(action) != 1 or s["phase"] not in ("check", "exam")):
                    return None
            prefix = ""
            phase = s["phase"]
            if action == "delete":
                del saved["routes"][route]
                self._save(db, key, saved)
                return "這座寶庫的學習進度已刪除，舊按鈕失效；其他路線保留。想重新出發，說一聲「學習」便好。", ()
            if action == "delete_prompt":
                s["nonce"] = secrets.token_hex(8)
                result = ("確定刪除目前這座寶庫的已通過階段與進度？此操作無法復原，其他路線不受影響。", (self._button(signing_key, s, "確認刪除", "delete"), self._button(signing_key, s, "保留進度", "map")))
            else:
                if action == "pause":
                    s.update(phase="paused", score=0, index=0, wrong=[])
                    prefix = "「歇一歇也好，我替你留著這一頁。」\n已暫停。已解鎖階段與教材位置會保留；未完成的挑戰下次重新開始。\n"
                elif action == "resume" and phase == "paused":
                    s["phase"] = "lesson"
                elif action.startswith("stage-"):
                    target = int(action[6:]) if action[6:].isdigit() else -1
                    if target < 0 or target > min(s["unlocked"], len(stages)-1):
                        return "請先通過前一階段，才能解鎖這段路線。自由提問不受限制。", ()
                    s.update(stage=target, lesson=0, phase="lesson", score=0, index=0, wrong=[])
                elif action == "check" and phase == "lesson":
                    s["phase"] = "check"
                elif action == "next" and phase == "review":
                    s["lesson"] += 1
                    s["phase"] = "ready" if s["lesson"] == 5 else "lesson"
                    s["lesson"] = min(s["lesson"], 4)
                elif action == "exam" and phase == "ready":
                    order = [q for _, q in stages[s["stage"]][1]]
                    secrets.SystemRandom().shuffle(order)
                    s.update(phase="exam", order=order, score=0, index=0, wrong=[])
                elif len(action) == 1 and action in "ABCD" and phase in ("check", "exam"):
                    q = self._question(s)
                    correct = action == q.correct_letter
                    prefix = ("「正是如此。」老人微微頷首。" if correct else "「不急，我們再看一次這裡的差別。」") + f"\n正解：{q.correct_letter}. {q.correct_text}\n{q.explanation}\n{q.source_url}\n\n"
                    if phase == "check":
                        if correct:
                            s["phase"] = "review"
                    else:
                        s["score"] += int(correct)
                        if not correct:
                            s["wrong"].append(q.id)
                        s["index"] += 1
                        if s["index"] == 5:
                            stage = s["stage"]
                            s["best"][str(stage)] = max(s["best"].get(str(stage), 0), s["score"])
                            passed = s["score"] >= 4
                            if passed:
                                s["unlocked"] = max(s["unlocked"], min(stage + 1, 3))
                            prefix += f"本次 {s['score']}/5，四題正確即可通過。\n" + ("通過！可從學習地圖選擇下一階段。" if passed else "尚未通過。看完下方補充後可以再挑戰，不扣除既有解鎖。")
                            if passed and stage == 3:
                                prefix += "\n這座寶庫的全部四階段，你已走過了。願這些答案，帶你遇見更多值得追問的事。"
                            for qid in s["wrong"]:
                                wrong = self.bank.by_id[qid]
                                prefix += f"\n\n複習：{wrong.prompt}\n{wrong.explanation}\n{wrong.source_url}"
                            s["phase"] = "ready"
                elif action not in ("map", "resume"):
                    return "目前不能執行這個步驟。請輸入「繼續學習」。", ()
                s["nonce"] = secrets.token_hex(8)
                result = self._render(signing_key, s, prefix, show_map=action == "map")
            self._save(db, key, saved)
            return result

    @staticmethod
    def _save(db, key, saved):
        db.execute("INSERT INTO learning_v1 VALUES (?,?) ON CONFLICT(user_key) DO UPDATE SET state=excluded.state", (key, json.dumps(saved, ensure_ascii=False)))
        db.commit()

    @staticmethod
    def _route_menu():
        text = "「你對這世界感到好奇嗎？」\n\n老人攤開星圖，四座寶庫的名字映入眼簾。\n\n"
        text += "\n".join(f"{VAULTS[key].name}：{VAULTS[key].description}" for key in ROUTE_COMMANDS.values())
        text += "\n\n「選一條你想走的路吧。不必急著懂得一切，我們從第一個問題開始。」\n四條路線各自記錄進度，隨時可以換路或自由提問。進度保存在機器人伺服器，不會存取你的手機資料。"
        return text, tuple(QuickReplyOption(VAULTS[key].name, message_text=f"學習路線 {key}") for key in ROUTE_COMMANDS.values())

    def _question(self, s):
        qid = s["order"][s["index"]] if s["phase"] == "exam" else self.routes[s["route"]][s["stage"]][1][s["lesson"]][1]
        return self.bank.by_id[qid]

    def _render(self, key, s, prefix="", *, show_map=False):
        button = lambda label, action: self._button(key, s, label, action)
        stages = self.routes[s["route"]]
        route_name = VAULTS[s["route"]].name
        switch = QuickReplyOption("選擇其他寶庫", message_text="學習")
        if show_map or s["phase"] == "paused":
            lines = [f"{route_name}｜學習地圖"]
            options = []
            for i, (title, _) in enumerate(stages):
                opened = i <= s["unlocked"]
                best = s["best"].get(str(i), 0)
                lines.append(f"{i+1}. {title} {'已通過' if best >= 4 else '可學習' if opened else '待解鎖'}，最高 {best}/5")
                if opened:
                    options.append(button(f"{i+1}. {title}", f"stage-{i}"))
            options.append(button("繼續目前進度", "resume"))
            options.append(switch)
            return prefix + "\n".join(lines) + "\n每階段五段短講與理解題，五題挑戰答對四題可進階。隨時自由提問。", tuple(options)
        title, lessons = stages[s["stage"]]
        heading = f"{route_name} {s['stage']+1}/4｜{title}\n"
        common = (button("學習地圖", "map"), button("暫停學習", "pause"), switch)
        phase = s["phase"]
        if phase == "lesson":
            card_id, qid = lessons[s["lesson"]]
            card, q = self.knowledge.by_id.get(card_id), self.bank.by_id[qid]
            content = f"第 {s['lesson']+1}/5 段：{card.canonical_question if card else q.prompt}\n"
            if card:
                content += "\n".join(card.facts) + f"\n來源：{card.source_url}\n"
            content += f"\n先記住這個概念：{q.correct_text}。\n{q.explanation}\n依據：{q.source_url}\n\n「若有哪裡不明白，就停下來問我。想清楚了，再試試下方的理解題。」"
            return prefix + heading + content, (button("理解題", "check"),) + common
        if phase in ("check", "exam"):
            q = self._question(s)
            content = (f"過關挑戰 {s['index']+1}/5" if phase == "exam" else "小理解題") + f"\n{q.prompt}\n"
            content += "\n".join(f"{letter}. {choice}" for letter, choice in zip("ABCD", q.choices))
            return prefix + heading + content, tuple(button(letter, letter) for letter in "ABCD") + common
        if phase == "review":
            return prefix + heading + "理解題完成。可以繼續追問，或前往下一段。", (button("下一段", "next"),) + common
        return prefix + "\n" + heading + "五段教材已完成，可開始五題過關挑戰。", (button("過關挑戰", "exam"),) + common
