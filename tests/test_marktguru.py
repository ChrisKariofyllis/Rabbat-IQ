import httpx
import pytest

from app.adapters.marktguru import (
    MarktguruAdapter,
    keep_flyer,
    leaflets_by_chain,
    parse_homepage_keys,
    parse_flight,
    offer_link,
    merge_store_lists,
    parse_offer,
    place_from_locations,
    selected_industries,
)
from app.domain import Flyer, GeoPlace, StoreLocation
from app.geo import stores_from_nominatim, stores_from_overpass
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


def test_offer_link_skips_generic_pages():
    site = "https://www.marktguru.de"
    assert offer_link({"id": 11, "externalUrl": None}, site=site) == "https://www.marktguru.de/offers/11"
    assert (
        offer_link({"id": 11, "externalUrl": "https://www.lidl.de/p/energy/p100410253"}, site=site)
        == "https://www.lidl.de/p/energy/p100410253"
    )
    article = "https://filiale.kaufland.de/angebote/uebersicht.html?kloffer-articleID=20897900"
    assert offer_link({"id": 11, "externalUrl": article}, site=site) == article
    category = "https://filiale.kaufland.de/angebote/uebersicht.html?kloffer-category=0001_TopArticle"
    assert offer_link({"id": 11, "externalUrl": category}, site=site) == "https://www.marktguru.de/offers/11"
    search = "https://www.marktguru.de/suche?q=Energy+Drink"
    assert offer_link({"id": 11, "externalUrl": search}, site=site) == "https://www.marktguru.de/offers/11"
    tracker = "https://ad.doubleclick.net/ddm/trackclk/N1.site/B2"
    assert offer_link({"id": 11, "externalUrl": tracker}, site=site) == "https://www.marktguru.de/offers/11"
    assert "suche?q=" not in offer_link({"id": 11, "product": {"name": "Energy Drink"}}, site=site)


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


def test_flyer_scope_labels_a_single_booklet_as_local():
    local = parse_flight(
        {"id": 1, "mainLeafletId": 9, "spreadLeaflet": False, "leafletCount": 1, "advertiser": {"name": "Lidl"}},
        cdn="https://cdn.marktguru.de",
        site="https://www.marktguru.de",
    )
    broader = parse_flight(
        {"id": 2, "mainLeafletId": 8, "spreadLeaflet": True, "leafletCount": 21, "advertiser": {"name": "EDEKA"}},
        cdn="https://cdn.marktguru.de",
        site="https://www.marktguru.de",
    )
    assert local.scope == "local"
    assert broader.scope == "broader"


def test_place_from_locations_prefers_the_named_town():
    place = place_from_locations(
        [
            {"name": "Sinzing Adlstein", "latitude": 48.9766, "longitude": 11.9426, "zipCodes": ["93161"]},
            {"name": "Sinzing", "latitude": 48.99028, "longitude": 12.03750, "zipCodes": ["93161"]},
            {"name": "Sinzing Alling", "latitude": 48.98328, "longitude": 11.97819, "zipCodes": ["93161"]},
        ],
        "93161",
        "de",
    )
    assert place is not None
    assert place.name == "Sinzing"
    assert place.latitude == pytest.approx(48.99028)
    assert place.longitude == pytest.approx(12.03750)


def test_place_from_locations_uses_the_postal_centroid():
    place = place_from_locations(
        [
            {"name": "Sinzing Adlstein", "latitude": 48.9766, "longitude": 11.9426, "zipCodes": ["93161"]},
            {"name": "Sinzing Alling", "latitude": 48.9959, "longitude": 12.0544, "zipCodes": ["93161"]},
            {"name": "Other town", "latitude": 50.0, "longitude": 10.0, "zipCodes": ["10115"]},
        ],
        "93161",
        "de",
    )
    assert place is not None
    assert place.name == "Sinzing"
    assert place.latitude == pytest.approx((48.9766 + 48.9959) / 2)
    assert place.longitude == pytest.approx((11.9426 + 12.0544) / 2)
    assert place.postal_code == "93161"


def test_merge_keeps_a_branch_the_leaflet_omits():
    netto = StoreLocation("1", "Netto Marken-Discount Sinzing", "Netto Marken-Discount", "", "93161", "Sinzing", 48.9907, 12.0292, 600, "", "marktguru")
    edeka = StoreLocation("osm-node-1", "EDEKA", "EDEKA", "Am Reitfeld 8a", "93161", "Sinzing", 48.9950, 12.0324, 650, "", "openstreetmap")
    duplicate = StoreLocation("osm-node-2", "Netto Marken-Discount", "Netto Marken-Discount", "", "93161", "Sinzing", 48.9908, 12.0293, 610, "", "openstreetmap")
    merged = merge_store_lists([netto], [duplicate, edeka])
    assert [store.chain for store in merged] == ["Netto Marken-Discount", "EDEKA"]


def test_overpass_keeps_supermarkets_inside_the_radius():
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 9,
                "lat": 48.9950,
                "lon": 12.0324,
                "tags": {"name": "EDEKA", "brand": "EDEKA", "addr:postcode": "93161", "addr:street": "Am Reitfeld", "addr:housenumber": "8a"},
            },
            {
                "type": "node",
                "id": 10,
                "lat": 49.05,
                "lon": 12.10,
                "tags": {"name": "Far", "brand": "Lidl"},
            },
        ]
    }
    stores = stores_from_overpass(payload, 48.99028, 12.03750, 2000)
    assert [store.name for store in stores] == ["EDEKA"]
    assert stores[0].postal_code == "93161"
    assert stores[0].distance_m < 1000


def test_nominatim_keeps_a_named_branch_inside_the_radius():
    stores = stores_from_nominatim(
        [
            {
                "lat": "48.9950344",
                "lon": "12.0323854",
                "display_name": "EDEKA, Am Reitfeld, Sinzing, 93161, Deutschland",
                "osm_type": "node",
                "osm_id": 42,
                "address": {"shop": "EDEKA", "road": "Am Reitfeld", "house_number": "8a", "postcode": "93161", "town": "Sinzing"},
            }
        ],
        "EDEKA",
        48.99028,
        12.03750,
        2000,
    )
    assert len(stores) == 1
    assert stores[0].chain == "EDEKA"
    assert stores[0].distance_m < 1000
    assert stores[0].postal_code == "93161"


def test_leaflets_by_chain_keeps_smaller_booklets():
    big = Flyer("big", "Netto", "Netto", "Discounter", None, None, 8, 300, "", source_url="")
    local = Flyer("local", "Netto", "Netto", "Discounter", None, None, 4, 20, "", source_url="")
    chosen = leaflets_by_chain([big, local])
    assert [item.external_id for item in chosen] == ["big", "local"]


def _store(store_id: str, name: str, lat: float, lon: float):
    return {
        "id": store_id,
        "name": name,
        "storeChainName": "Netto",
        "location": {
            "latitude": lat,
            "longitude": lon,
            "address": name,
            "zipCodes": ["93161"],
            "name": "Sinzing",
        },
        "distanceInMeters": 9000,
    }


@pytest.mark.asyncio
async def test_nearby_stores_keeps_the_local_branch():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/leaflets/big/stores"):
            return httpx.Response(200, json={"results": [_store("far", "Netto Regensburg", 49.05, 12.10)]})
        if path.endswith("/leaflets/local/stores"):
            return httpx.Response(200, json={"results": [_store("near", "Netto Sinzing", 48.986, 11.999)]})
        return httpx.Response(404, json={})

    place = GeoPlace("93161", "Sinzing", 48.9863, 11.9985, "de")
    flyers = [
        Flyer("big", "Netto", "Netto", "Discounter", None, None, 8, 300, ""),
        Flyer("local", "Netto", "Netto", "Discounter", None, None, 4, 20, ""),
    ]
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = MarktguruAdapter(api_key="secret", client=client, delay=0)
        async with adapter:
            stores = await adapter.nearby_stores(place, flyers, 4000)
    assert [store.name for store in stores] == ["Netto Sinzing"]
    assert stores[0].distance_m < 4000
