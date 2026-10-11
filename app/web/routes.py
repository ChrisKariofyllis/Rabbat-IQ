"""HTML pages and a small JSON API for the scan status poller."""

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.ai.providers import AIError, ai_configured, complete
from app.bot.runner import bot_runner
from app.config import get_env
from app.formatting import format_when
from app.notifications.telegram import TelegramError, send_message
from app.services import repository
from app.services.scan import is_scanning, scan_status, try_start_scan
from app.textutil import extract_json
from app.web.forms import CATEGORY_OPTIONS, COUNTRIES, PROVIDERS, parse_settings_form, settings_form_values
from app.textutil import same_chain
from app.web.present import (
    NAV,
    flyer_view,
    interest_offers,
    match_view,
    notice_text,
    offer_view,
    scan_view,
    store_chain_options,
    store_views,
)

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
router = APIRouter()

INTEREST_NOTICES = {
    "added": "interest",
    "duplicate": "duplicate",
    "empty": "empty",
    "long": "long",
    "limit": "limit",
}


def page_context(request: Request, active: str, **extra) -> dict:
    settings = repository.get_settings()
    status = scan_status()
    context = {
        "request": request,
        "active": active,
        "nav": NAV,
        "settings": settings,
        "scanning": status["running"] or is_scanning(),
        "ready": bool((settings.postal_code or "").strip()) and bool(repository.list_interests()),
        "match_count": repository.count_matches(),
        "scheduler_on": not get_env().disable_scheduler,
        "notice": notice_text(request.query_params.get("notice")),
        "error": "",
        "poll": request.query_params.get("poll") == "1",
        "place_label": _place_label(settings),
    }
    context.update(extra)
    return context


def _place_label(settings) -> str:
    parts = []
    if settings.place_name:
        parts.append(settings.place_name)
    if settings.postal_code:
        parts.append(settings.postal_code)
    radius = settings.radius_km or 0
    if settings.postal_code:
        parts.append(f"{radius:g} km")
    return " · ".join(parts)


@router.get("/")
def overview(request: Request):
    settings = repository.get_settings()
    stores = repository.list_stores()
    flyer_rows = repository.list_flyers()
    flyers = [flyer_view(row) for row in flyer_rows[:4]]
    matches = [match_view(row) for row in repository.list_matches(limit=6)]
    interests = repository.list_interests()
    status = scan_view(scan_status())
    checklist = [
        {"label": "Postal code and radius", "done": bool(settings.postal_code), "href": "/settings"},
        {"label": "At least one interest", "done": bool(interests), "href": "/interests"},
        {
            "label": "AI key, if you want semantic or vision matching",
            "done": ai_configured(settings.ai_provider, settings.ai_api_key, settings.ai_base_url),
            "href": "/settings",
            "optional": True,
        },
        {
            "label": "Telegram bot, if you want alerts",
            "done": bool(settings.telegram_bot_token and settings.telegram_chat_id),
            "href": "/settings",
            "optional": True,
        },
    ]
    return templates.TemplateResponse(
        request,
        "overview.html",
        page_context(
            request,
            "overview",
            stats={
                "stores": len(stores),
                "flyers": len(flyer_rows),
                "offers": len(repository.list_offers()),
                "matches": repository.count_matches(),
            },
            matches=matches,
            flyers=flyers,
            checklist=checklist,
            scan=status,
            show_setup=not (settings.postal_code and interests),
        ),
    )


@router.get("/stores")
def stores_page(request: Request, store: str = ""):
    settings = repository.get_settings()
    rows = repository.list_stores()
    chains = store_chain_options(rows)
    selected = store.strip()
    if selected and not any(same_chain(selected, chain) for chain in chains):
        selected = ""
    visible = rows
    if selected:
        visible = [row for row in rows if same_chain(row.chain, selected) or same_chain(row.name, selected)]
    home = (settings.latitude, settings.longitude)
    points, home_point = store_views(visible, home)
    interests = [row.text for row in repository.list_interests()]
    deals = []
    for offer, label in interest_offers(repository.list_offers(), rows, interests, selected):
        view = offer_view(offer)
        view["interest"] = label
        deals.append(view)
    return templates.TemplateResponse(
        request,
        "stores.html",
        page_context(
            request,
            "stores",
            stores=points,
            home=home_point,
            has_map=home_point is not None or any(point["x"] is not None for point in points),
            chains=chains,
            selected_store=selected,
            store_offers=deals,
            has_interests=bool(interests),
        ),
    )


@router.get("/flyers")
def flyers_page(request: Request):
    flyers = [flyer_view(row) for row in repository.list_flyers()]
    return templates.TemplateResponse(request, "flyers.html", page_context(request, "flyers", flyers=flyers))


@router.get("/flyers/{flyer_id}")
def flyer_page(request: Request, flyer_id: int):
    row = repository.get_flyer(flyer_id)
    if row is None:
        return templates.TemplateResponse(
            request,
            "404.html",
            page_context(request, "flyers"),
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "flyer.html",
        page_context(request, "flyers", flyer=flyer_view(row)),
    )


@router.get("/offers")
async def offers_page(request: Request, q: str = ""):
    query = " ".join(q.split())[:80]
    saved = [offer_view(row) for row in repository.list_offers()]
    live: list[dict] = []
    error = ""
    if query:
        live, error = await _live_search(query)
    return templates.TemplateResponse(
        request,
        "offers.html",
        page_context(request, "offers", saved=saved, live=live, query=query, search_error=error),
    )


@router.get("/matches")
def matches_page(request: Request):
    matches = [match_view(row) for row in repository.list_matches(limit=200)]
    return templates.TemplateResponse(request, "matches.html", page_context(request, "matches", matches=matches))


@router.post("/matches/clear")
def clear_matches():
    repository.clear_matches()
    return RedirectResponse("/matches?notice=cleared", status_code=303)


@router.get("/interests")
def interests_page(request: Request):
    return templates.TemplateResponse(
        request,
        "interests.html",
        page_context(request, "interests", interests=repository.list_interests()),
    )


@router.post("/interests")
def add_interest(text: str = Form("")):
    result = repository.add_interest(text)
    code = INTEREST_NOTICES.get(result, "empty")
    return RedirectResponse(f"/interests?notice={code}", status_code=303)


@router.post("/interests/{interest_id}/delete")
def remove_interest(interest_id: int):
    removed = repository.delete_interest(interest_id)
    code = "removed" if removed else "missing"
    return RedirectResponse(f"/interests?notice={code}", status_code=303)


@router.get("/settings")
def settings_page(request: Request):
    return _settings_response(request)


@router.post("/settings")
async def save_settings(request: Request):
    form = await request.form()
    current = repository.get_settings()
    data, errors = parse_settings_form(form, current)
    if data is None:
        return _settings_response(request, errors=errors, form_values=_posted_settings(form, current))
    repository.update_settings(**data)
    await bot_runner.sync()
    return RedirectResponse("/settings?notice=saved", status_code=303)


@router.post("/settings/test-telegram")
async def test_telegram(request: Request):
    settings = repository.get_settings()
    token = (settings.telegram_bot_token or "").strip()
    chat_id = (settings.telegram_chat_id or "").strip()
    if not token or not chat_id:
        return _settings_response(request, errors=["Save a bot token and chat id before sending a test."])
    try:
        await send_message(token, chat_id, "Rabbat-IQ is connected. Deal alerts will arrive in this chat.")
    except TelegramError as exc:
        return _settings_response(request, errors=[f"Telegram did not accept the test. {exc}"])
    return _settings_response(request, notice="Test message sent.")


@router.post("/settings/test-ai")
async def test_ai(request: Request):
    settings = repository.get_settings()
    if not ai_configured(settings.ai_provider, settings.ai_api_key, settings.ai_base_url):
        return _settings_response(request, errors=["Add an API key, or choose Ollama and a base URL, before testing."])
    try:
        raw = await complete(
            provider=settings.ai_provider,
            model=settings.ai_model,
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            system="Reply with JSON only.",
            user_text='Return {"ok": true}',
        )
        extract_json(raw)
    except (AIError, ValueError) as exc:
        return _settings_response(request, errors=[f"The model could not be reached. {exc}"])
    return _settings_response(request, notice="The model replied with JSON.")


@router.post("/scan")
async def start_scan():
    if not repository.get_settings().postal_code or not repository.list_interests():
        return RedirectResponse("/?notice=need-setup", status_code=303)
    outcome = try_start_scan("manual")
    if outcome == "busy":
        return RedirectResponse("/?notice=busy&poll=1", status_code=303)
    return RedirectResponse("/?notice=scan&poll=1", status_code=303)


@router.get("/api/scan/status")
def scan_status_api():
    status = scan_status()
    last = status["last"]
    if last:
        last = {
            **last,
            "started_at": _iso(last.get("started_at")),
            "finished_at": _iso(last.get("finished_at")),
        }
    return {
        "running": status["running"],
        "next_scan_at": _iso(status.get("next_scan_at")),
        "last": last,
    }


@router.get("/api/stores")
def stores_api():
    points, _home = store_views(repository.list_stores())
    return points


@router.get("/api/matches")
def matches_api():
    return [match_view(row) for row in repository.list_matches(limit=100)]


@router.get("/robots.txt")
def robots():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


def _settings_response(request: Request, errors: list[str] | None = None, notice: str = "", form_values: dict | None = None):
    settings = repository.get_settings()
    values = form_values or settings_form_values(settings)
    context = page_context(request, "settings")
    context["form"] = values
    context["errors"] = errors or []
    context["countries"] = COUNTRIES
    context["categories"] = CATEGORY_OPTIONS
    context["providers"] = PROVIDERS
    context["sources"] = _sources()
    if notice:
        context["notice"] = notice
    return templates.TemplateResponse(request, "settings.html", context)


def _posted_settings(form, current) -> dict:
    values = settings_form_values(current)
    values.update(
        {
            "postal_code": str(form.get("postal_code") or ""),
            "country": str(form.get("country") or "de"),
            "radius_km": form.get("radius_km") or values["radius_km"],
            "scan_interval_minutes": form.get("scan_interval_minutes") or values["scan_interval_minutes"],
            "preferred_stores": str(form.get("preferred_stores") or ""),
            "categories": [item for item in form.getlist("categories")],
            "match_mode": str(form.get("match_mode") or "keyword"),
            "min_confidence": form.get("min_confidence") or values["min_confidence"],
            "vision_enabled": bool(form.get("vision_enabled")),
            "vision_max_pages": form.get("vision_max_pages") or values["vision_max_pages"],
            "ai_provider": str(form.get("ai_provider") or "openai"),
            "ai_model": str(form.get("ai_model") or ""),
            "ai_base_url": str(form.get("ai_base_url") or ""),
            "telegram_chat_id": str(form.get("telegram_chat_id") or ""),
        }
    )
    return values


def _sources():
    from app.adapters.registry import catalog

    return catalog()


async def _live_search(query: str) -> tuple[list[dict], str]:
    from app.adapters.marktguru import AdapterError
    from app.adapters.registry import build_marktguru

    settings = repository.get_settings()
    if not (settings.postal_code or "").strip():
        return [], "Set a postal code before searching live offers."
    adapter = build_marktguru(settings)
    try:
        async with adapter:
            place = await adapter.geocode(settings.postal_code, settings.country or "de")
            if place is None:
                return [], "That postal code could not be located."
            offers = await adapter.search_offers(place, query, limit=24)
    except AdapterError as exc:
        return [], str(exc)
    return [offer_view(offer) for offer in offers], ""


def _iso(value) -> str | None:
    if value is None:
        return None
    return format_when(value)


def render_not_found(request: Request):
    return templates.TemplateResponse(request, "404.html", page_context(request, ""), status_code=404)
