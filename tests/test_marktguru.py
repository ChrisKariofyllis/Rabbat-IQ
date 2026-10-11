import httpx
import pytest

from app.adapters.marktguru import (
    MarktguruAdapter,
    keep_flyer,
    parse_homepage_keys,
    parse_offer,
    selected_industries,
)
from app.domain import GeoPlace
from app.textutil import extract_json, parse_price, same_chain

SAMPLE = {
    "id": 25289747,
    "description": "1,5 % Fett, je 500-g-Becher",
    "price": 0.59,
    "oldPrice": 0.89,
    "referencePrice": 1.18,
    "externalUrl": "https://filiale.example/offer",
    "validityDates": [{"from": "2026-10-14T22:00:00Z", "to": "2026-10-17T21:59:00Z"}],
    "brand": {"name": "K-Classic"},
    "advertisers": [{"name": "Kaufland"}],
    "product": {"name": "Joghurt"},
    "unit": {"shortName": "kg"},
}


def test_parse_offer_uses_public_image_and_price():
    parsed = parse_offer(SAMPLE, cdn="https://cdn.marktguru.de", site="https://www.marktguru.de")
    assert parsed.product == "Joghurt"
    assert parsed.price == 0.59
    assert parsed.chain == "Kaufland"
    assert parsed.image_url.endswith("/offers/25289747/images/default/0/medium.jpg")
    assert parsed.link_url == "https://filiale.example/offer"
    assert parsed.valid_to is not None


def test_homepage_keys_and_industry_filter():
    html = '<script type="application/json">{"config":{"apiKey":"abc123456789","clientKey":"client"}}</script>'
    assert parse_homepage_keys(html) == ("abc123456789", "client")
    assert selected_industries(["grocery", "hardware"]) == {
        "Supermarkt",
        "Discounter",
        "Biomarkt",
        "Getränkemarkt",
        "Essen & Genießen",
        "Baumarkt",
    }
    assert selected_industries(["all"]) is None
    assert keep_flyer("Möbelhaus", "XXXLutz", selected_industries(["grocery"]), []) is False
    assert keep_flyer("Discounter", "Lidl", selected_industries(["grocery"]), ["Aldi"]) is False
    assert keep_flyer("Discounter", "ALDI SÜD", selected_industries(["grocery"]), ["Aldi"]) is True


def test_text_helpers():
    assert same_chain("Aldi", "ALDI SÜD")
    assert not same_chain("Hit", "White")
    assert parse_price("0,59 €") == 0.59
    assert parse_price("1.299,00 €") == 1299.0
    assert extract_json('```json\n{"matches":[]}\n```') == {"matches": []}


@pytest.mark.asyncio
async def test_search_sends_zip_and_key():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["zip"] = request.url.params["zipCode"]
        seen["query"] = request.url.params["q"]
        seen["key"] = request.headers["x-apikey"]
        return httpx.Response(200, json={"results": [SAMPLE], "totalResults": 1})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = MarktguruAdapter(api_key="secret", client_key="client", client=client, delay=0)
        async with adapter:
            offers = await adapter.search_offers(
                GeoPlace("10115", "Berlin Mitte", 52.53, 13.4, "de"),
                "joghurt",
                limit=5,
            )
    assert seen == {"zip": "10115", "query": "joghurt", "key": "secret"}
    assert offers[0].brand == "K-Classic"
