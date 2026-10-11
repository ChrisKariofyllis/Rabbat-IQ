from fastapi.testclient import TestClient

from app.config import EnvSettings
from app.main import create_app
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


def test_basic_auth_protects_pages_but_not_health(tmp_path):
    with make_client(tmp_path, basic_auth_user="ada", basic_auth_password="secret") as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 401
        authed = client.get("/", auth=("ada", "secret"))
        assert authed.status_code == 200
        assert "Rabbat-IQ" in authed.text
