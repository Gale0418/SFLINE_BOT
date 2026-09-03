from __future__ import annotations

import csv
import hashlib
import hmac
import secrets
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from random import Random, SystemRandom
from typing import Callable


LETTERS = "ABCD"


@dataclass(frozen=True, slots=True)
class VaultInfo:
    key: str
    name: str
    description: str


VAULTS = {
    "cosmos": VaultInfo("cosmos", "🌌 星海之庫", "宇宙、恆星、行星與天文觀測"),
    "living_world": VaultInfo("living_world", "🌍 地脈與生命之庫", "地球、海洋、演化、人體與腦"),
    "laws": VaultInfo("laws", "⚛️ 萬象法則之庫", "經典物理、相對論、量子與材料"),
    "future": VaultInfo("future", "🚀 未來幻夢之庫", "能源、AI、太空工程與科幻邊界"),
    "all": VaultInfo("all", "🗝️ 群星寶庫", "四座寶庫混合，考驗跨領域判斷"),
}

DIFFICULTY_NAMES = {
    "easy": "見習",
    "medium": "遠征",
    "hard": "守門人",
    "mixed": "命運混合",
}

SOURCE_CATALOG = {
    "nasa_universe": ("NASA Science — Universe", "https://science.nasa.gov/universe/"),
    "nasa_stars": ("NASA Science — Stars", "https://science.nasa.gov/universe/stars/"),
    "nasa_solar": ("NASA Science — Solar System", "https://science.nasa.gov/solar-system/"),
    "nasa_exoplanets": ("NASA Science — Exoplanets", "https://science.nasa.gov/exoplanets/how-we-find-and-characterize/"),
    "eht": ("Event Horizon Telescope Collaboration", "https://eventhorizontelescope.org/"),
    "usgs_plates": ("USGS — This Dynamic Earth", "https://pubs.usgs.gov/gip/dynamic/"),
    "usgs_quakes": ("USGS — Earthquake Hazards Program", "https://www.usgs.gov/programs/earthquake-hazards"),
    "noaa_climate": ("NOAA Climate.gov", "https://www.climate.gov/"),
    "noaa_ocean": ("NOAA Ocean Service", "https://oceanservice.noaa.gov/"),
    "smithsonian_evolution": ("Smithsonian Human Origins Program", "https://humanorigins.si.edu/evidence/human-evolution"),
    "nih_brain": ("NIH/NINDS — Brain Basics", "https://www.ninds.nih.gov/health-information/public-education/brain-basics"),
    "nih_body": ("NIH — How the Human Body Works", "https://www.nih.gov/health-information"),
    "nist_physics": ("NIST Physical Measurement Laboratory", "https://www.nist.gov/pml"),
    "einstein_online": ("Einstein Online", "https://www.einstein-online.info/en/"),
    "ligo": ("LIGO Laboratory", "https://www.ligo.caltech.edu/page/what-are-gw"),
    "doe_quantum": ("U.S. Department of Energy — Quantum Information Science", "https://www.energy.gov/science/quantum-information-science"),
    "cern": ("CERN — Physics", "https://home.cern/science/physics"),
    "acs": ("American Chemical Society", "https://www.acs.org/education/resources/highschool/chemmatters.html"),
    "nasa_climate": ("NASA Science — Climate Change", "https://science.nasa.gov/climate-change/"),
    "doe_energy": ("U.S. Department of Energy", "https://www.energy.gov/science-innovation/energy-sources"),
    "nist_ai": ("NIST — AI Risk Management Framework", "https://www.nist.gov/itl/ai-risk-management-framework"),
    "nasa_technology": ("NASA — Space Technology Mission Directorate", "https://www.nasa.gov/spacetech/"),
    "alcubierre": ("Miguel Alcubierre — The Warp Drive", "https://arxiv.org/abs/gr-qc/0009013"),
    "morris_thorne": ("Morris and Thorne — Traversable Wormholes", "https://arxiv.org/abs/gr-qc/9302026"),
}


class QuizError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    id: str
    vault: str
    topic: str
    difficulty: str
    prompt: str
    choices: tuple[str, str, str, str]
    correct_letter: str
    explanation: str
    source_key: str

    @property
    def correct_text(self) -> str:
        return self.choices[LETTERS.index(self.correct_letter)]

    @property
    def source_name(self) -> str:
        return SOURCE_CATALOG[self.source_key][0]

    @property
    def source_url(self) -> str:
        return SOURCE_CATALOG[self.source_key][1]


class QuizBank:
    def __init__(self, questions: list[QuizQuestion]) -> None:
        self.questions = tuple(questions)
        self.by_id = {question.id: question for question in questions}
        self._validate()

    @classmethod
    def load(cls, path: str | Path) -> "QuizBank":
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        required = {
            "id", "vault", "topic", "difficulty", "question", "choice_a", "choice_b",
            "choice_c", "choice_d", "correct", "explanation", "source_key",
        }
        if not rows or set(rows[0]) != required:
            raise QuizError("題庫欄位不符合規格")
        questions: list[QuizQuestion] = []
        for index, row in enumerate(rows, start=2):
            try:
                questions.append(
                    QuizQuestion(
                        id=row["id"].strip(),
                        vault=row["vault"].strip(),
                        topic=row["topic"].strip(),
                        difficulty=row["difficulty"].strip(),
                        prompt=row["question"].strip(),
                        choices=(
                            row["choice_a"].strip(), row["choice_b"].strip(),
                            row["choice_c"].strip(), row["choice_d"].strip(),
                        ),
                        correct_letter=row["correct"].strip().upper(),
                        explanation=row["explanation"].strip(),
                        source_key=row["source_key"].strip(),
                    )
                )
            except Exception as exc:
                raise QuizError(f"題庫第 {index} 列格式無效") from exc
        return cls(questions)

    def _validate(self) -> None:
        if len(self.questions) != 96 or len(self.by_id) != 96:
            raise QuizError("題庫必須包含 96 題且 ID 不可重複")
        formal_vaults = set(VAULTS) - {"all"}
        difficulties = set(DIFFICULTY_NAMES) - {"mixed"}
        for question in self.questions:
            if not all((question.id, question.topic, question.prompt, question.explanation)):
                raise QuizError(f"題目 {question.id} 含空白必要欄位")
            if question.vault not in formal_vaults or question.difficulty not in difficulties:
                raise QuizError(f"題目 {question.id} 的寶庫或難度無效")
            if question.correct_letter not in LETTERS:
                raise QuizError(f"題目 {question.id} 的正解位置無效")
            if len(set(question.choices)) != 4 or any(not choice for choice in question.choices):
                raise QuizError(f"題目 {question.id} 必須有四個不同選項")
            if question.source_key not in SOURCE_CATALOG:
                raise QuizError(f"題目 {question.id} 的來源代號不存在")
            if len(question.prompt) > 260 or max(map(len, question.choices)) > 80:
                raise QuizError(f"題目 {question.id} 超過 LINE 顯示安全長度")

        vault_counts = Counter(question.vault for question in self.questions)
        if vault_counts != Counter({vault: 24 for vault in formal_vaults}):
            raise QuizError("四座正式寶庫必須各有 24 題")
        pair_counts = Counter((question.vault, question.difficulty) for question in self.questions)
        if pair_counts != Counter({(vault, difficulty): 8 for vault in formal_vaults for difficulty in difficulties}):
            raise QuizError("每座寶庫的三種難度必須各有 8 題")
        topic_counts = Counter(question.topic for question in self.questions)
        if len(topic_counts) != 16 or set(topic_counts.values()) != {6}:
            raise QuizError("題庫必須涵蓋 16 個主題且每個主題 6 題")
        for vault in formal_vaults:
            for difficulty in difficulties:
                positions = Counter(
                    question.correct_letter
                    for question in self.questions
                    if question.vault == vault and question.difficulty == difficulty
                )
                if positions != Counter({letter: 2 for letter in LETTERS}):
                    raise QuizError(f"{vault}/{difficulty} 的正解位置必須平均分布")

    def select(self, *, vault: str, difficulty: str) -> tuple[QuizQuestion, ...]:
        if vault not in VAULTS or difficulty not in DIFFICULTY_NAMES:
            raise QuizError("未知的寶庫或難度")
        return tuple(
            question
            for question in self.questions
            if (vault == "all" or question.vault == vault)
            and (difficulty == "mixed" or question.difficulty == difficulty)
        )


@dataclass(slots=True)
class QuizSession:
    id: str
    vault: str
    difficulty: str
    questions: tuple[QuizQuestion, ...]
    index: int
    score: int
    streak: int
    best_streak: int
    touched_at: float

    @property
    def current_question(self) -> QuizQuestion:
        return self.questions[self.index]

    @property
    def answered(self) -> int:
        return self.index

    @property
    def total(self) -> int:
        return len(self.questions)


@dataclass(frozen=True, slots=True)
class QuizOutcome:
    question: QuizQuestion
    chosen_letter: str
    correct: bool
    score: int
    answered: int
    total: int
    best_streak: int
    completed: bool
    next_question: QuizQuestion | None
    session_id: str
    vault: str
    difficulty: str


class QuizManager:
    def __init__(
        self,
        bank: QuizBank,
        *,
        salt: str,
        ttl_seconds: int = 1800,
        question_count: int = 5,
        max_sessions: int = 1000,
        clock: Callable[[], float] = time.monotonic,
        random_source: Random | SystemRandom | None = None,
    ) -> None:
        self.bank = bank
        self._salt = salt.encode("utf-8")
        self._ttl_seconds = ttl_seconds
        self._question_count = question_count
        self._max_sessions = max_sessions
        self._clock = clock
        self._random = random_source or SystemRandom()
        self._sessions: dict[str, QuizSession] = {}
        self._lock = threading.Lock()

    def _user_key(self, user_id: str) -> str:
        return hashlib.sha256(self._salt + b":" + user_id.encode("utf-8")).hexdigest()

    def _purge(self, now: float) -> None:
        expired = [key for key, value in self._sessions.items() if now - value.touched_at > self._ttl_seconds]
        for key in expired:
            self._sessions.pop(key, None)

    def start(self, user_id: str, *, vault: str, difficulty: str) -> QuizSession:
        eligible = self.bank.select(vault=vault, difficulty=difficulty)
        if len(eligible) < self._question_count:
            raise QuizError("符合條件的題目不足")
        now = self._clock()
        selected = tuple(self._random.sample(list(eligible), self._question_count))
        session = QuizSession(
            id=secrets.token_urlsafe(9),
            vault=vault,
            difficulty=difficulty,
            questions=selected,
            index=0,
            score=0,
            streak=0,
            best_streak=0,
            touched_at=now,
        )
        key = self._user_key(user_id)
        with self._lock:
            self._purge(now)
            if key not in self._sessions and len(self._sessions) >= self._max_sessions:
                oldest = min(self._sessions, key=lambda item: self._sessions[item].touched_at)
                self._sessions.pop(oldest, None)
            self._sessions[key] = session
        return session

    def current(self, user_id: str) -> QuizSession | None:
        key = self._user_key(user_id)
        now = self._clock()
        with self._lock:
            self._purge(now)
            session = self._sessions.get(key)
            if session is not None:
                session.touched_at = now
            return session

    def quit(self, user_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(self._user_key(user_id), None) is not None

    def answer_token(self, user_id: str, session: QuizSession, letter: str) -> str:
        letter = letter.upper()
        question = session.current_question
        user_key = self._user_key(user_id)
        payload = f"{session.id}|{question.id}|{letter}|{user_key}"
        signature = hmac.new(self._salt, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
        return f"ep:a:{session.id}:{question.id}:{letter}:{signature}"

    def submit_text(self, user_id: str, letter: str) -> QuizOutcome:
        return self._submit(user_id, letter.upper(), session_id=None, question_id=None, signature=None)

    def submit_postback(self, user_id: str, data: str) -> QuizOutcome:
        parts = data.split(":")
        if len(parts) != 7 or parts[:2] != ["ep", "a"]:
            raise QuizError("答案符文格式無效")
        _, _, session_id, question_id, letter, signature, marker = parts
        if marker != "v1":
            raise QuizError("答案符文版本無效")
        return self._submit(user_id, letter.upper(), session_id, question_id, signature)

    def _submit(
        self,
        user_id: str,
        letter: str,
        session_id: str | None,
        question_id: str | None,
        signature: str | None,
    ) -> QuizOutcome:
        if letter not in LETTERS:
            raise QuizError("答案必須是 A、B、C 或 D")
        key = self._user_key(user_id)
        now = self._clock()
        with self._lock:
            self._purge(now)
            session = self._sessions.get(key)
            if session is None:
                raise QuizError("沒有進行中的試煉")
            question = session.current_question
            if session_id is not None:
                if session_id != session.id or question_id != question.id or signature is None:
                    raise QuizError("答案不屬於目前題目")
                payload = f"{session.id}|{question.id}|{letter}|{key}"
                expected = hmac.new(self._salt, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:20]
                if not hmac.compare_digest(signature, expected):
                    raise QuizError("答案符文驗證失敗")
            correct = letter == question.correct_letter
            if correct:
                session.score += 1
                session.streak += 1
                session.best_streak = max(session.best_streak, session.streak)
            else:
                session.streak = 0
            session.index += 1
            session.touched_at = now
            completed = session.index >= session.total
            next_question = None if completed else session.current_question
            outcome = QuizOutcome(
                question=question,
                chosen_letter=letter,
                correct=correct,
                score=session.score,
                answered=session.answered,
                total=session.total,
                best_streak=session.best_streak,
                completed=completed,
                next_question=next_question,
                session_id=session.id,
                vault=session.vault,
                difficulty=session.difficulty,
            )
            if completed:
                self._sessions.pop(key, None)
            return outcome


def answer_postback_data(manager: QuizManager, user_id: str, session: QuizSession, letter: str) -> str:
    return manager.answer_token(user_id, session, letter) + ":v1"
