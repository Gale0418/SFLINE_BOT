from eternal_polaris.knowledge_images import (
    FEATURED_IMAGE_FILES,
    FEATURED_KNOWLEDGE_IDS,
    image_filename_for_sources,
)


def test_featured_gallery_has_exactly_one_hundred_unique_cards(knowledge):
    assert len(FEATURED_KNOWLEDGE_IDS) == 100
    assert len(set(FEATURED_KNOWLEDGE_IDS)) == 100
    assert set(FEATURED_KNOWLEDGE_IDS) <= set(knowledge.by_id)
    assert len(FEATURED_IMAGE_FILES) == 100


def test_answer_uses_first_curated_source_image():
    assert image_filename_for_sources(("not-featured", "sw009", "sw012")) == "card-sw009.jpg"
    assert image_filename_for_sources(("not-featured",)) == ""
