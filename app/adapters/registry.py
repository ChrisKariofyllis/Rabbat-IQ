"""Which offer sources a scan actually calls."""

from app.adapters.marktguru import MarktguruAdapter, selected_industries
from app.config import get_env
from app.services.repository import get_settings


def catalog() -> list[dict]:
    return [
        {
            "id": "marktguru",
            "label": "Marktguru",
            "state": "Active",
            "detail": "Offers, leaflets, and store distance for Germany and Austria.",
        },
        {
            "id": "chain_template",
            "label": "Direct chain scraper",
            "state": "Add your own",
            "detail": "Copy app/adapters/chain_template.py and register the class to add a store website.",
        },
    ]


def build_marktguru(settings=None) -> MarktguruAdapter:
    settings = settings or get_settings()
    env = get_env()
    return MarktguruAdapter(
        country=settings.country or "de",
        api_key=env.marktguru_api_key,
        client_key=env.marktguru_client_key,
        data_dir=env.data_dir,
    )


def industries_from_settings(settings) -> set[str] | None:
    categories = [part.strip() for part in (settings.categories or "").split(",") if part.strip()]
    return selected_industries(categories)
