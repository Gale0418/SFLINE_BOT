from __future__ import annotations

from collections.abc import Sequence


# Ten deliberately balanced galleries, ten cards each.  The list favours
# foundational ideas, strong visual explanations, the guided-learning themes,
# and the Taiwan-local material that gives Eternal Polaris its own identity.
FEATURED_KNOWLEDGE_IDS = (
    # Solar System portraits
    "sw001", "sw002", "sw003", "sw004", "sw005",
    "sw006", "sw007", "sw008", "sw009", "sw012",
    # Small bodies, moons, and our cosmic address
    "ov024", "sw014", "sw016", "sw017", "sw019",
    "sw020", "sw021", "sw023", "sw038", "sw040",
    # Planetary environments and first settlements
    "sw029", "sw033", "sw057", "sw058", "sw060",
    "sw061", "sw063", "sw068", "sw073", "sw079",
    # Alien plants and possible life
    "sw085", "sw090", "sw091", "sw094", "sw095",
    "sw096", "sw098", "sw100", "sw102", "sw1173",
    # Worlds used by science fiction
    "sw105", "sw106", "sw107", "sw108", "sw109",
    "sw111", "sw113", "sw114", "sw115", "sw120",
    # Space history and megastructures
    "sw124", "sw129", "sw131", "sw133", "sw137",
    "sw141", "sw143", "sw146", "sw148", "sw150",
    # Interstellar travel and faster-than-light ideas
    "sw151", "sw155", "sw156", "sw157", "sw159",
    "sw162", "sw164", "sw165", "sw167", "sw168",
    # Stars, black holes, nebulae, and cosmic distance
    "sw171", "sw173", "sw180", "sw184", "sw188",
    "sw190", "sw191", "sw301", "sw336", "sw339",
    # Science-fiction technology and future life
    "sw252", "sw254", "sw256", "sw261", "sw262",
    "sw263", "sw265", "sw271", "sw288", "sw299",
    # Taiwan stargazing and signature future-world topics
    "sw1151", "sw1155", "sw1156", "sw1157", "sw1159",
    "sw1163", "sw1164", "sw1168", "sw1177", "sw1180",
)

FEATURED_IMAGE_FILES = frozenset(
    f"card-{card_id}.jpg" for card_id in FEATURED_KNOWLEDGE_IDS
)


def image_filename_for_sources(source_ids: Sequence[str]) -> str:
    """Return the first curated illustration supported by an answer citation."""
    featured = set(FEATURED_KNOWLEDGE_IDS)
    return next(
        (f"card-{source_id}.jpg" for source_id in source_ids if source_id in featured),
        "",
    )
