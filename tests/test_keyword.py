from datetime import datetime, timezone

from app.ai.glossary import queries_for_interest
from app.ai.keyword import keyword_matches, score_interest
from app.domain import Offer, StoreLocation


def offer(**overrides) -> Offer:
    data = dict(
        external_id="1",
        source="marktguru",
        product="Joghurt",
        description="griechischer Art, 500 g",
        brand="K-Classic",
        price=0.59,
        old_price=0.89,
        unit="kg",
        reference_price=1.18,
        chain="Kaufland",
        store_name="Kaufland",
        valid_from=datetime(2026, 10, 12, tzinfo=timezone.utc),
        valid_to=datetime(2026, 10, 18, tzinfo=timezone.utc),
        image_url="https://cdn.marktguru.de/example.jpg",
        link_url="https://example.test/offer",
    )
    data.update(overrides)
    return Offer(**data)


def test_english_interests_search_the_german_index():
    assert queries_for_interest("beer") == ["Bier OR Pils"]
    assert queries_for_interest("Greek yogurt") == ["griechisch Joghurt"]
    assert "Parkside" in queries_for_interest("Parkside tools")
    assert queries_for_interest("Werkzeugkasten") == ["Werkzeugkasten OR Werkzeug"]


def test_exact_and_synonym_scores():
    words = ["griechischer", "joghurt", "k", "classic", "kaufland"]
    assert score_interest(words, "Joghurt")[0] == 0.88
    assert score_interest(words, "Greek yogurt")[0] == 0.76
    assert score_interest(words, "Werkzeugkasten") is None


def test_single_token_does_not_match_inside_another_word():
    assert score_interest(["sale", "butter"], "ale") is None


def test_beer_glossary_and_tools():
    assert score_interest(["pils", "kastan"], "beer")[0] == 0.76
    assert score_interest(["parkside", "werkzeugkasten"], "Parkside tools") is not None


def test_keyword_match_builds_a_stable_draft():
    stores = [
        StoreLocation(
            external_id="9",
            name="Kaufland Berlin-Moabit",
            chain="Kaufland",
            address="Perleberger Straße 42",
            postal_code="10559",
            city="Berlin",
            latitude=52.53,
            longitude=13.34,
            distance_m=700,
            opening_hours="Mo-Sa 07:00-22:00",
            source="marktguru",
        )
    ]
    drafts = keyword_matches([offer()], ["Greek yogurt"], stores, min_confidence=0.55)
    assert len(drafts) == 1
    assert drafts[0].store_name == "Kaufland Berlin-Moabit"
    assert drafts[0].discount == "−34%"
    assert drafts[0].fingerprint == keyword_matches([offer()], ["Greek yogurt"], stores, 0.55)[0].fingerprint
    assert keyword_matches([offer()], ["Greek yogurt"], stores, min_confidence=0.99) == []
