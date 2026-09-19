from __future__ import annotations

import csv
import hashlib
import hmac
import secrets
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from random import Random, SystemRandom

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
    "movie_film": ("Sony Pictures Taiwan — 極限返航", "https://stg.sonypictures.com.tw/movies/jixianfanhang-project-hail-mary"),
    "movie_potato": ("NASA — 深空糧食作物研究", "https://www.nasa.gov/science-research/nasa-plant-researchers-explore-question-of-deep-space-food-crops/"),
    "movie_toxic": ("NASA — 火星高氯酸鹽處理研究", "https://www.nasa.gov/general/detoxifying-mars/"),
    "movie_relativity": ("Einstein Online — 雙生子與時間", "https://www.einstein-online.info/en/spotlight/twins/"),
    "movie_consult": ("NASA — 極限返航科學諮詢", "https://www.nasa.gov/general/nasa-exploration-science-inspire-project-hail-mary-film/"),
    "solar_yr4": ("NASA — 2024 YR4", "https://science.nasa.gov/solar-system/asteroids/2024-yr4-facts/"),
    "solar_meteors": ("NASA — 流星與隕石", "https://science.nasa.gov/solar-system/meteors-meteorites/"),
    "solar_address": ("NASA — 太陽系的位置", "https://science.nasa.gov/solar-system/solar-system-facts/"),
    "solar_galaxies": ("NASA — 宇宙大尺度結構", "https://science.nasa.gov/universe/galaxies/large-scale-structures/"),
    "solar_parker": ("NASA — Parker 最近太陽飛掠紀錄", "https://science.nasa.gov/science-research/heliophysics/nasas-parker-solar-probe-makes-history-with-closest-pass-to-sun/"),
    "solar_proxima": ("ESA/Hubble — 比鄰星", "https://esahubble.org/images/potw1343a/"),
    "solar_mercury": ("NASA — 水星", "https://science.nasa.gov/mercury/facts/"),
    "solar_venus": ("NASA — 金星", "https://science.nasa.gov/venus/venus-facts/"),
    "solar_earth": ("NASA — 地球", "https://science.nasa.gov/earth/facts/"),
    "solar_mars": ("NASA — 火星", "https://science.nasa.gov/mars/facts/"),
    "solar_jupiter": ("NASA — 木星", "https://science.nasa.gov/jupiter/jupiter-facts/"),
    "solar_saturn": ("NASA — 土星", "https://science.nasa.gov/saturn/facts/"),
    "solar_uranus": ("NASA — 天王星", "https://science.nasa.gov/uranus/facts/"),
    "solar_neptune": ("NASA — 海王星", "https://science.nasa.gov/neptune/neptune-facts/"),
    "solar_sun": ("NASA — 太陽", "https://science.nasa.gov/sun/facts/"),
    "solar_ice": ("LLNL — 超離子冰的原子結構", "https://www.llnl.gov/article/45336/giant-lasers-crystallize-water-shockwaves-revealing-atomic-structure-superionic-ice"),
    "solar_pluto": ("NASA — 冥王星", "https://science.nasa.gov/dwarf-planets/pluto/facts/"),
    "solar_asteroids": ("NASA — 小行星", "https://science.nasa.gov/solar-system/asteroids/facts/"),
    "solar_comets": ("NASA — 彗星", "https://science.nasa.gov/solar-system/comets/facts/"),
    "solar_atlas": ("NASA — 3I/ATLAS FAQ", "https://science.nasa.gov/solar-system/comets/3i-atlas/3i-atlas-facts-and-faqs/"),
    "solar_europa": ("NASA — 為什麼探索木衛二", "https://science.nasa.gov/mission/europa-clipper/why-europa-overview/"),
    "solar_enceladus": ("NASA — 土衛二", "https://science.nasa.gov/saturn/moons/enceladus/"),
    "solar_phobos": ("NASA — 火衛一", "https://science.nasa.gov/mars/moons/phobos/"),
    "solar_io": ("NASA — 木衛一", "https://science.nasa.gov/jupiter/jupiter-moons/io/facts/"),
    "solar_ganymede": ("NASA — 木衛三", "https://science.nasa.gov/jupiter/jupiter-moons/ganymede/facts/"),
    "solar_titan": ("NASA — 土衛六", "https://science.nasa.gov/saturn/moons/titan/facts/"),
    "solar_triton": ("NASA — 海衛一", "https://science.nasa.gov/neptune/moons/triton/"),
    "dwarf_overview": ("NASA — 矮行星總覽", "https://science.nasa.gov/dwarf-planets/"),
    "dwarf_ceres": ("NASA — 穀神星", "https://science.nasa.gov/dwarf-planets/ceres/facts/"),
    "dwarf_makemake": ("NASA — 鳥神星", "https://science.nasa.gov/dwarf-planets/makemake/"),
    "iau_planet": ("IAU — 太陽系行星定義", "https://iau.org/Iau/Publications/List-of-Resolutions"),
    "asteroid_apophis": ("NASA — 阿波菲斯", "https://science.nasa.gov/solar-system/asteroids/apophis-facts/"),
    "asteroid_bennu": ("NASA — 貝努", "https://science.nasa.gov/solar-system/asteroids/101955-bennu/facts/"),
    "asteroid_dart": ("NASA — Didymos 與 Dimorphos", "https://science.nasa.gov/solar-system/asteroids/didymos/"),
    "asteroid_psyche": ("NASA — 靈神星", "https://science.nasa.gov/solar-system/asteroids/16-psyche/"),
    "asteroid_lucy": ("NASA — Lucy 任務", "https://science.nasa.gov/mission/lucy/"),
    "comet_halley": ("NASA — 哈雷彗星", "https://science.nasa.gov/solar-system/comets/1p-halley/"),
    "comet_67p": ("NASA — 67P 彗星", "https://science.nasa.gov/solar-system/comets/67p-churyumov-gerasimenko/"),
    "meteor_geminids": ("NASA — 雙子座流星雨", "https://science.nasa.gov/solar-system/meteors-meteorites/geminids/"),
    "solar_kuiper": ("NASA — 古柏帶", "https://science.nasa.gov/solar-system/kuiper-belt/facts/"),
    "solar_oort": ("NASA — 歐特雲", "https://science.nasa.gov/solar-system/oort-cloud/facts/"),
    "solar_heliosphere": ("NASA — 太陽系邊界", "https://science.nasa.gov/resource/where-is-the-edge-of-the-solar-system/"),
    "mission_voyager2": ("NASA — 航海家二號", "https://science.nasa.gov/mission/voyager/voyager-2/"),
    "mission_travel": ("NASA — 前往月球、火星與木星要多久", "https://www.nasa.gov/directorates/smd/how-long-does-it-take-to-get-to-the-moon-mars-jupiter-we-asked-a-nasa-expert-episode-51/"),
    "movie_blackhole": ("NASA — 黑洞附近的時間與潮汐", "https://science.nasa.gov/universe/what-happens-when-something-gets-too-close-to-a-black-hole/"),
    "movie_sound": ("NASA — 太空中的聲音", "https://science.nasa.gov/science-research/planetary-science/01nov_ismsounds/"),
    "movie_debris": ("NASA — 微流星體與軌道碎片", "https://www.nasa.gov/centers-and-facilities/white-sands/micrometeoroids-and-orbital-debris-mmod/"),
    "movie_artificial_gravity": ("NASA NTRS — 人工重力", "https://ntrs.nasa.gov/citations/20030033919"),
    "fun_ov022": ("USGS — 地球內部", "https://pubs.usgs.gov/gip/interior/"),
    "fun_ov023": ("NASA — 臭氧洞是什麼", "https://ozonewatch.gsfc.nasa.gov/facts/hole_SH.html"),
    "fun_ov024": ("NASA Space Place — 藍天", "https://spaceplace.nasa.gov/blue-sky/en/"),
    "fun_ov025": ("NOAA NESDIS — 彩虹成因", "https://www.nesdis.noaa.gov/about/k-12-education/optical-phenomena/what-causes-rainbow"),
    "fun_ov026": ("NASA — 月亮常見問題", "https://science.nasa.gov/moon/top-moon-questions/"),
    "fun_ov027": ("NOAA Ocean Exploration — 章魚的三顆心", "https://oceanexplorer.noaa.gov/news/exploration-extras/22valentines/media/octopus.pdf"),
    "fun_ov028": ("英國南極調查局 — 極地海洋", "https://www.bas.ac.uk/news/state-of-the-polar-oceans-report-published/"),
    "fun_ov029": ("英國自然史博物館 — 存活的恐龍", "https://www.nhm.ac.uk/discover/why-are-birds-the-only-surviving-dinosaurs.html"),
    "fun_ov030": ("NASA — 金星資料", "https://science.nasa.gov/venus/venus-facts/"),
    "fun_ov031": ("NASA Cassini — 土星環常見問題", "https://science.nasa.gov/mission/cassini/faq/"),
    "fun_ov032": ("NASA Space Place — 極光", "https://spaceplace.nasa.gov/aurora/en/"),
    "fun_ov033": ("NASA — 電磁波與機械波", "https://science.nasa.gov/ems/02_anatomy/"),
    "history_ov019": ("美國國會圖書館 — 宇宙模型史", "https://www.loc.gov/collections/finding-our-place-in-the-cosmos-with-carl-sagan/articles-and-essays/modeling-the-cosmos/"),
    "history_ov020": ("美國國會圖書館 — 日心宇宙", "https://www.loc.gov/exhibits/exploring-the-early-americas/interactives/heavens-and-earth/heavens/artifact10-heaven.html"),
    "history_ov021": ("伽利略博物館 — 生平年表", "https://www.museogalileo.it/en/galileo/life.html"),
    "history_ov011": ("美國國會圖書館 — 月球上的居民與生物", "https://www.loc.gov/collections/finding-our-place-in-the-cosmos-with-carl-sagan/articles-and-essays/life-on-other-worlds/peoples-and-creatures-of-the-moon/"),
    "history_ov012": ("NASA — 水手四號的成就", "https://science.nasa.gov/mars/triumph-of-mariner-4/"),
    "history_ov013": ("英國自然史博物館 — 皮爾當人", "https://www.nhm.ac.uk/our-science/services/library/collections/piltdown-man.html"),
    "history_ov014": ("NASA/JPL — 2012科學查核", "https://www.jpl.nasa.gov/videos/2012-a-scientific-reality-check/"),
    "history_ov015": ("NASA — 所謂火星人臉", "https://science.nasa.gov/photojournal/the-so-called-face-on-mars/"),
    "history_ov016": ("劍橋丘吉爾檔案中心 — 尋找脈衝星", "https://archives.chu.cam.ac.uk/collections/research-guides/misc-109/"),
    "history_sf009": ("Sony Pictures — 2012", "https://www.sonypictures.com/movies/2012"),
    "history_ov017": ("美國政府問責署GAO — Y2K風險治理回顧", "https://files.gao.gov/reports/105184/index.html"),
    "history_ov018": ("諾斯特拉達穆斯原詩 — 1867年版本第十卷第72首", "https://fr.wikisource.org/wiki/Page%3ANostradamus_-_Les_oracles_-1867.djvu/224"),
    "loc_halley": ("美國國會圖書館 — 哈雷彗星歷史報刊", "https://guides.loc.gov/chronicling-america-halleys-comet"),
    "loc_radio": ("美國國會圖書館 — 世界大戰廣播", "https://blogs.loc.gov/loc/2016/10/lcm-page-from-the-past-war-of-the-worlds/"),
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
    def load(cls, path: str | Path) -> QuizBank:
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
        # Editorial TSV files are optimized for readability, not for where the
        # correct option happens to sit. Reposition choices deterministically
        # at load time so every 8-question vault/difficulty block has exactly
        # two A/B/C/D answers. The correct text and every distractor are kept;
        # only their positions change. This permanently prevents answer-letter
        # bias from creeping back in when questions are edited.
        return cls(cls._rebalance_answer_positions(questions))

    @staticmethod
    def _rebalance_answer_positions(questions: list[QuizQuestion]) -> list[QuizQuestion]:
        grouped: dict[tuple[str, str], list[QuizQuestion]] = {}
        for question in questions:
            grouped.setdefault((question.vault, question.difficulty), []).append(question)

        rebalanced: dict[str, QuizQuestion] = {}
        for (vault, difficulty), group in grouped.items():
            ordered = sorted(group, key=lambda question: question.id)
            digest = hashlib.sha256(f"{vault}:{difficulty}".encode()).digest()
            offset = digest[0] % len(LETTERS)
            for index, question in enumerate(ordered):
                target_letter = LETTERS[(index + offset) % len(LETTERS)]
                rebalanced[question.id] = QuizBank._move_correct_choice(question, target_letter)

        return [rebalanced.get(question.id, question) for question in questions]

    @staticmethod
    def _move_correct_choice(question: QuizQuestion, target_letter: str) -> QuizQuestion:
        if question.correct_letter not in LETTERS or target_letter not in LETTERS:
            return question
        correct_index = LETTERS.index(question.correct_letter)
        correct_text = question.choices[correct_index]
        distractors = [
            choice for index, choice in enumerate(question.choices) if index != correct_index
        ]
        rebuilt: list[str] = []
        distractor_index = 0
        for letter in LETTERS:
            if letter == target_letter:
                rebuilt.append(correct_text)
            else:
                rebuilt.append(distractors[distractor_index])
                distractor_index += 1
        return replace(
            question,
            choices=(rebuilt[0], rebuilt[1], rebuilt[2], rebuilt[3]),
            correct_letter=target_letter,
        )

    def _validate(self) -> None:
        if len(self.questions) < 220 or len(self.by_id) != len(self.questions):
            raise QuizError("題庫不得少於原始220題，且 ID 不可重複")
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

        pair_counts = Counter((question.vault, question.difficulty) for question in self.questions)
        baseline_difficulties = {
            "cosmos": (54, 38, 14),
            "living_world": (16, 13, 8),
            "laws": (12, 10, 8),
            "future": (20, 19, 8),
        }
        for vault, counts in baseline_difficulties.items():
            for difficulty, minimum in zip(("easy", "medium", "hard"), counts, strict=True):
                if pair_counts[vault, difficulty] < minimum:
                    raise QuizError(f"{vault}/{difficulty} 不得少於原始題庫基線 {minimum} 題")
        topic_counts = Counter(question.topic for question in self.questions)
        expansion_baseline = {"科學史與媒體識讀": 20, "好奇心小學堂": 34, "太陽系驚奇之旅": 50, "電影裡的科學": 20}
        if len(topic_counts) < 20 or any(topic_counts[topic] < count for topic, count in expansion_baseline.items()):
            raise QuizError("須保留原20主題與既有擴充內容；允許繼續增加新主題與題目")
        for vault in formal_vaults:
            for difficulty in difficulties:
                positions = Counter(
                    question.correct_letter
                    for question in self.questions
                    if question.vault == vault and question.difficulty == difficulty
                )
                if max(positions[letter] for letter in LETTERS) - min(positions[letter] for letter in LETTERS) > 1:
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
        if ttl_seconds < 1 or question_count < 1 or max_sessions < 1:
            raise ValueError("quiz TTL、題數與場次容量必須為正整數")
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
