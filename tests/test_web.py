from fastapi.testclient import TestClient

from app.config import EnvSettings
from app.domain import Offer, StoreLocation
from app.main import create_app
from app.services import repository
from app.services.scan import reset_scan_state


def make_client(tmp_path, **env):
    reset_scan_state()
    app = create_app(
        EnvSettings(
            database_url=f"sqlite:///{tmp_path / 'web.db'}",
            data_dir=str(tmp_path),
            disable_scheduler=True,
            disable_bot=True,
            **env,
        )
    )
    return TestClient(app)


def test_pages_settings_and_interests(tmp_path):
    with make_client(tmp_path) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "Rabbat-IQ" in home.text
        assert "Set up this machine" in home.text

        saved = client.post(
            "/settings",
            data={
                "postal_code": "10115",
                "country": "de",
                "radius_km": "5",
                "scan_interval_minutes": "30",
                "preferred_stores": "Lidl, Rewe",
                "categories": "grocery",
                "match_mode": "keyword",
                "min_confidence": "0.55",
                "vision_max_pages": "3",
                "ai_provider": "openai",
                "ai_model": "",
                "ai_base_url": "http://127.0.0.1:11434",
                "telegram_chat_id": "",
            },
            follow_redirects=True,
        )
        assert saved.status_code == 200
        assert "Settings saved." in saved.text
        assert 'value="10115"' in saved.text

        rejected = client.post(
            "/settings",
            data={
                "postal_code": "12",
                "country": "de",
                "radius_km": "5",
                "scan_interval_minutes": "30",
                "categories": "grocery",
                "match_mode": "keyword",
                "min_confidence": "0.55",
                "vision_max_pages": "3",
                "ai_provider": "openai",
                "ai_base_url": "http://127.0.0.1:11434",
            },
        )
        assert rejected.status_code == 200
        assert "5 digits" in rejected.text

        added = client.post("/interests", data={"text": "Greek yogurt"}, follow_redirects=True)
        assert "Greek yogurt" in added.text
        duplicate = client.post("/interests", data={"text": "greek yogurt"}, follow_redirects=True)
        assert "already on your list" in duplicate.text

        stores = client.get("/stores")
        offers = client.get("/offers")
        matches = client.get("/matches")
        flyers = client.get("/flyers")
        assert stores.status_code == offers.status_code == matches.status_code == flyers.status_code == 200
        assert client.get("/no-such-page").status_code == 404
        assert client.get("/health").json()["ok"] is True
        assert client.get("/robots.txt").text.startswith("User-agent")


def test_saved_search_links_open_the_offer_page(tmp_path):
    with make_client(tmp_path) as client:
        repository.replace_offers(
            [
                Offer(
                    "25289747",
                    "marktguru",
                    "Joghurt",
                    "",
                    "",
                    0.59,
                    None,
                    "",
                    None,
                    "Kaufland",
                    "Kaufland",
                    None,
                    None,
                    "",
                    "https://www.marktguru.de/suche?q=Joghurt",
                )
            ]
        )
        page = client.get("/offers")
        assert "https://www.marktguru.de/offers/25289747" in page.text
        assert "suche?q=" not in page.text


def test_store_page_filters_interest_offers(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/interests", data={"text": "yogurt"})
        repository.replace_stores(
            [
                StoreLocation("1", "Netto Sinzing", "Netto", "Hauptstr", "93161", "Sinzing", 48.9, 11.9, 2000, "", "marktguru"),
                StoreLocation("2", "NORMA Sinzing", "NORMA", "Dorf", "93161", "Sinzing", 48.91, 12.0, 2600, "", "marktguru"),
            ]
        )
        repository.replace_offers(
            [
                Offer("a", "marktguru", "Joghurt", "", "", 0.59, None, "", None, "Netto", "Netto", None, None, "", "https://www.marktguru.de/offers/a"),
                Offer("b", "marktguru", "Energy Drink", "", "", 0.99, None, "", None, "NORMA", "NORMA", None, None, "", "https://www.marktguru.de/offers/b"),
            ]
        )
        page = client.get("/stores")
        assert "All stores" in page.text
        assert "Netto Sinzing" in page.text
        assert "Joghurt" in page.text
        assert "Energy Drink" not in page.text
        assert 'id="store-map"' in page.text
        assert "var(--chain-netto)" in page.text
        assert "var(--chain-norma)" in page.text
        policy = page.headers["content-security-policy"]
        assert "tile.openstreetmap.fr" in policy
        assert "tile.openstreetmap.org" not in policy
        assert "basemaps.cartocdn.com" not in policy
        filtered = client.get("/stores", params={"store": "Netto"})
        assert "Netto Sinzing" in filtered.text
        assert "NORMA Sinzing" not in filtered.text
        assert "var(--chain-norma)" not in filtered.text
        assert "Joghurt" in filtered.text


def test_offers_page_can_keep_only_interest_matches(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/interests", data={"text": "yogurt"})
        repository.replace_offers(
            [
                Offer("a", "marktguru", "Joghurt", "", "", 0.59, None, "", None, "Netto", "Netto", None, None, "", "https://www.marktguru.de/offers/a"),
                Offer("b", "marktguru", "Energy Drink", "", "", 0.99, None, "", None, "NORMA", "NORMA", None, None, "", "https://www.marktguru.de/offers/b"),
            ]
        )
        everything = client.get("/offers")
        assert "Joghurt" in everything.text
        assert "Energy Drink" in everything.text
        assert "Only offers that match my interests" in everything.text
        filtered = client.get("/offers", params={"interests": "1"})
        assert "Joghurt" in filtered.text
        assert "Energy Drink" not in filtered.text
        assert "checked" in filtered.text


def test_store_map_centers_on_the_postal_code(tmp_path):
    with make_client(tmp_path) as client:
        repository.update_settings(
            postal_code="80331",
            country="de",
            radius_km=2,
            latitude=48.137,
            longitude=11.575,
        )
        repository.replace_stores(
            [
                StoreLocation(
                    "1",
                    "EDEKA Stadt",
                    "EDEKA",
                    "Marienplatz 1",
                    "80331",
                    "München",
                    48.138,
                    11.576,
                    120,
                    "Mo-Sa 08:00-20:00",
                    "marktguru",
                ),
                StoreLocation(
                    "2",
                    "Lidl Tal",
                    "Lidl",
                    "Tal 10",
                    "80331",
                    "München",
                    48.135,
                    11.581,
                    480,
                    "",
                    "marktguru",
                ),
            ]
        )
        page = client.get("/stores")
        assert page.status_code == 200
        assert '"lat": 48.137' in page.text
        assert '"radiusM": 2000.0' in page.text
        assert "var(--chain-edeka)" in page.text
        assert "var(--chain-lidl)" in page.text
        assert "Mo-Sa 08:00-20:00" in page.text
        assert "leaflet.js" in page.text


def test_basic_auth_protects_pages_but_not_health(tmp_path):
    with make_client(tmp_path, basic_auth_user="ada", basic_auth_password="secret") as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 401
        authed = client.get("/", auth=("ada", "secret"))
        assert authed.status_code == 200
        assert "Rabbat-IQ" in authed.text
