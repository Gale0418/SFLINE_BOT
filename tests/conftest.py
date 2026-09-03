from __future__ import annotations

from pathlib import Path

import pytest

from eternal_polaris.config import Settings
from eternal_polaris.knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def knowledge() -> KnowledgeBase:
    return KnowledgeBase.load(ROOT / "data" / "knowledge_cards.json")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="test-openai",
        line_channel_secret="test-line-secret",
        line_channel_access_token="test-line-token",
        knowledge_path=ROOT / "data" / "knowledge_cards.json",
    )

