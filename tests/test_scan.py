import asyncio

import pytest

from app.config import EnvSettings
from app.domain import Flyer, GeoPlace, Offer, StoreLocation
from app.main import create_app
from app.services import repository
from app.services.scan import is_scanning, reset_scan_state, run_scan, try_start_scan


class FakeSource:
    def __init__(self, offers):
        self.offers = offers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def geocode(self, postal_code, country):
        return GeoPlace(postal_code, "Berlin Mitte", 52.53, 13.4, country or "de")

    async def leaflets(self, place, industries, preferred):
        return [
            Flyer(
                external_id="6281953",
                title="Kaufland",
                chain="Kaufland",
                industry="Supermarkt",
                valid_from=None,
                valid_to=None,
                page_count=4,
                offer_count=10,
                cover_url="https://cdn.marktguru.de/cover.jpg",
                page_urls=["https://cdn.marktguru.de/cover.jpg"],
                source_url="https://www.marktguru.de/leaflets/6281953/page/0",
            )
        ]

    async def nearby_stores(self, place, flyers, radius_m):
        return [
            StoreLocation(
                external_id="104600",
                name="Kaufland Berlin-Moabit",
                chain="Kaufland",
                address="Perleberger Straße 42 A",
                postal_code="10559",
                city="Berlin",
                latitude=52.529,
                longitude=13.344,
                distance_m=700,
                opening_hours="Mo-Sa 07:00-22:00",
                source="marktguru",
            )
        ]

    async def search_offers(self, place, query, limit=24):
        return list(self.offers)


def sample_offer() -> Offer:
    return Offer(
        external_id="25289747",
        source="marktguru",
        product="Joghurt",
        description="griechischer Art",
        brand="K-Classic",
        price=0.59,
        old_price=None,
        unit="kg",
        reference_price=1.18,
        chain="Kaufland",
        store_name="Kaufland",
        valid_from=None,
        valid_to=None,
        image_url="",
        link_url="",
    )


@pytest.fixture
def app(tmp_path):
    reset_scan_state()
    application = create_app(
        EnvSettings(
            database_url=f"sqlite:///{tmp_path / 'scan.db'}",
            data_dir=str(tmp_path),
            disable_scheduler=True,
            disable_bot=True,
        )
    )
    yield application
    reset_scan_state()


@pytest.mark.asyncio
async def test_scan_is_idempotent_and_filters_chains(app):
    repository.update_settings(postal_code="10115", country="de", radius_km=5, match_mode="keyword")
    repository.add_interest("Greek yogurt")
    sent = []

    async def notify(rows):
        sent.append(list(rows))

    source = FakeSource([sample_offer()])
    first = await run_scan("test", sources=[source], notify=notify)
    second = await run_scan("test", sources=[source], notify=notify)

    assert first["matches_found"] == 1
    assert second["matches_found"] == 0
    assert len(sent) == 2
    assert len(sent[0]) == 1
    assert sent[1] == []
    assert repository.count_matches() == 1
    assert repository.list_stores()[0].name == "Kaufland Berlin-Moabit"
    assert repository.get_settings().place_name == "Berlin Mitte"

    assert repository.latest_scan().status == "ok"

    repository.update_settings(preferred_stores="Lidl")
    third = await run_scan("test", sources=[source], notify=notify)
    assert third["offers_seen"] == 0
    assert repository.count_matches() == 1


@pytest.mark.asyncio
async def test_background_scan_starts_on_the_event_loop(app):
    assert try_start_scan("manual") == "started"
    assert is_scanning()
    for _ in range(50):
        if not is_scanning():
            break
        await asyncio.sleep(0.02)
    assert not is_scanning()
    last = repository.latest_scan()
    assert last is not None
    assert last.status == "error"
    assert "postal code" in last.message
