"""Turn database rows into template-friendly dictionaries."""

import json

from app.adapters.marktguru import offer_link
from app.ai.keyword import score_interest
from app.formatting import discount_label, format_distance, format_euro, format_when, validity_label
from app.textutil import normalize, same_chain

NAV = (
    {"id": "overview", "href": "/", "label": "Overview"},
    {"id": "stores", "href": "/stores", "label": "Stores"},
    {"id": "flyers", "href": "/flyers", "label": "Flyers"},
    {"id": "offers", "href": "/offers", "label": "Offers"},
    {"id": "matches", "href": "/matches", "label": "Matches"},
    {"id": "interests", "href": "/interests", "label": "Interests"},
    {"id": "settings", "href": "/settings", "label": "Settings"},
)

# Longer labels first so "galeria kaufhof" stays Galeria and "mix markt" stays Mix.
CHAIN_TONES = (
    ("galeria", "galeria"),
    ("kaufhof", "galeria"),
    ("mix markt", "mix"),
    ("mixmarkt", "mix"),
    ("kaufland", "kaufland"),
    ("rossmann", "rossmann"),
    ("edeka", "edeka"),
    ("rewe", "rewe"),
    ("lidl", "lidl"),
    ("netto", "netto"),
    ("norma", "norma"),
    ("aldi", "aldi"),
    ("penny", "penny"),
    ("tegut", "tegut"),
    ("globus", "globus"),
    ("famila", "famila"),
    ("combi", "combi"),
    ("hornbach", "hornbach"),
    ("bauhaus", "bauhaus"),
    ("muller", "muller"),
    ("toom", "toom"),
    ("obi", "obi"),
    ("hit", "hit"),
    ("dm", "dm"),
)

FALLBACK_COUNT = 8

NOTICES = {
    "saved": "Settings saved.",
    "interest": "Interest added.",
    "duplicate": "That interest is already on your list.",
    "removed": "Interest removed.",
    "scan": "Scan started. This page refreshes when it finishes.",
    "busy": "A scan is already running.",
    "scanned": "Scan finished.",
    "scan-failed": "The scan stopped early. The note below explains why.",
    "need-setup": "Add a postal code and at least one interest before scanning.",
    "cleared": "Match history cleared.",
    "long": "Keep an interest under 80 characters.",
    "limit": "You can save up to 30 interests.",
    "empty": "Write an interest before adding it.",
    "missing": "That interest is no longer on the list.",
}


def notice_text(code: str | None) -> str:
    return NOTICES.get(code or "", "")


def store_chain_options(stores) -> list[str]:
    options: list[str] = []
    seen: set[str] = set()
    for store in stores:
        label = (getattr(store, "chain", "") or getattr(store, "name", "") or "").strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        options.append(label)
    return options


def matched_interest(offer, interests: list[str]) -> str:
    words = normalize(
        " ".join(
            [
                getattr(offer, "product", "") or "",
                getattr(offer, "brand", "") or "",
                getattr(offer, "description", "") or "",
            ]
        )
    ).split()
    best = ""
    best_score = 0.0
    for interest in interests:
        scored = score_interest(words, interest)
        if scored and scored[0] >= best_score:
            best_score = scored[0]
            best = interest
    return best


def interest_offers(offers, stores, interests: list[str], selected: str = ""):
    """Offers that match an interest and belong to a saved nearby store."""

    local = [(getattr(store, "chain", "") or "", getattr(store, "name", "") or "") for store in stores]
    chosen = []
    for offer in offers:
        chain = getattr(offer, "chain", "") or ""
        name = getattr(offer, "store_name", "") or ""
        if local and not _belongs_to_store(chain, name, local):
            continue
        if selected and not (same_chain(chain, selected) or same_chain(name, selected)):
            continue
        label = matched_interest(offer, interests)
        if interests and not label:
            continue
        chosen.append((offer, label))
    return chosen


def _belongs_to_store(chain: str, name: str, local: list[tuple[str, str]]) -> bool:
    for store_chain, store_name in local:
        if same_chain(chain, store_chain) or same_chain(chain, store_name) or same_chain(name, store_chain):
            return True
    return False


def offer_view(offer) -> dict:
    price = getattr(offer, "price", None)
    old = getattr(offer, "old_price", None)
    reference = getattr(offer, "reference_price", None)
    return {
        "product": getattr(offer, "product", "") or "Offer",
        "description": getattr(offer, "description", "") or "",
        "brand": getattr(offer, "brand", "") or "",
        "chain": getattr(offer, "chain", "") or "",
        "store_name": getattr(offer, "store_name", "") or "",
        "price": format_euro(price),
        "old_price": format_euro(old) if old and price is not None and old > price else "",
        "discount": discount_label(price, old),
        "when": validity_label(getattr(offer, "valid_from", None), getattr(offer, "valid_to", None)),
        "image_url": getattr(offer, "image_url", "") or "",
        "link_url": _public_link(offer),
        "unit": getattr(offer, "unit", "") or "",
        "reference_price": format_euro(reference) if reference else "",
    }


def _public_link(offer) -> str:
    raw = getattr(offer, "link_url", "") or ""
    external_id = str(getattr(offer, "external_id", "") or "")
    site = "https://www.marktguru.at" if "marktguru.at" in raw else "https://www.marktguru.de"
    if not external_id and raw:
        return raw
    return offer_link({"id": external_id, "externalUrl": raw}, site=site)


def match_view(row) -> dict:
    view = offer_view(row)
    view.update(
        {
            "id": row.id,
            "interest": row.interest,
            "reason": row.reason,
            "confidence": f"{round((row.confidence or 0) * 100)}%",
            "store_name": row.store_name or row.chain,
            "notified": bool(row.notified_at),
            "notify_error": row.notify_error or "",
            "created": format_when(row.created_at),
        }
    )
    return view


SCOPE_LABELS = {
    "local": "Local",
    "broader": "Broader",
}


def flyer_view(row) -> dict:
    scope = getattr(row, "scope", "") or ""
    return {
        "id": row.id,
        "title": row.title or row.chain or "Flyer",
        "chain": row.chain or "",
        "industry": row.industry or "",
        "when": validity_label(row.valid_from, row.valid_to),
        "page_count": row.page_count or 0,
        "offer_count": row.offer_count or 0,
        "cover_url": row.cover_url or "",
        "pages": _pages(row.pages_json),
        "source_url": row.source_url or "",
        "scope": scope,
        "scope_label": SCOPE_LABELS.get(scope, "For this postal code"),
    }


def store_views(stores, home: tuple[float | None, float | None] | None = None) -> tuple[list[dict], dict | None]:
    views = []
    for index, store in enumerate(stores, start=1):
        view = _store_dict(store)
        if view["id"] is None:
            view["id"] = index
        views.append(view)
    return views, _home_point(home)


def map_payload(stores: list[dict], home: dict | None, radius_m: float | None) -> dict:
    plotted = []
    for store in stores:
        if store["lat"] is None or store["lon"] is None:
            continue
        plotted.append(
            {
                "id": store["id"],
                "name": store["name"],
                "lat": store["lat"],
                "lon": store["lon"],
                "color": store["color"],
                "tone": store["tone"],
            }
        )
    return {
        "home": home,
        "radiusM": None if home is None else radius_m,
        "stores": plotted,
    }


def scan_view(status: dict) -> dict:
    last = status.get("last")
    return {
        "running": status.get("running", False),
        "message": "" if not last else last.get("message") or "",
        "status": "" if not last else last.get("status") or "",
        "trigger": "" if not last else last.get("trigger") or "",
        "when": "" if not last else format_when(last.get("finished_at") or last.get("started_at")),
        "next": format_when(status.get("next_scan_at")),
        "stores_found": 0 if not last else last.get("stores_found") or 0,
        "flyers_found": 0 if not last else last.get("flyers_found") or 0,
        "offers_seen": 0 if not last else last.get("offers_seen") or 0,
        "matches_found": 0 if not last else last.get("matches_found") or 0,
    }


def _store_dict(store) -> dict:
    color, tone = chain_color(store.chain or store.name)
    return {
        "id": getattr(store, "id", None),
        "name": store.name,
        "chain": store.chain or "",
        "address": store.address or "",
        "city": store.city or "",
        "postal_code": store.postal_code or "",
        "distance": format_distance(store.distance_m),
        "hours": store.opening_hours or "",
        "lat": store.latitude,
        "lon": store.longitude,
        "color": color,
        "tone": tone,
    }


def _home_point(home: tuple[float | None, float | None] | None) -> dict | None:
    if not home or home[0] is None or home[1] is None:
        return None
    return {"lat": float(home[0]), "lon": float(home[1])}


def chain_color(name: str) -> tuple[str, str]:
    """CSS color variable shared by the list dot and the map pin."""

    tone = chain_tone(name)
    if tone:
        return f"var(--chain-{tone})", tone
    key = normalize(name) or "store"
    index = sum(ord(char) for char in key) % FALLBACK_COUNT
    return f"var(--chain-fallback-{index + 1})", ""


def chain_tone(name: str) -> str:
    text = normalize(name)
    if not text:
        return ""
    for needle, tone in CHAIN_TONES:
        if text == needle or text.startswith(needle + " "):
            return tone
        if len(needle) >= 4 and text.startswith(needle):
            return tone
    return ""


def _pages(raw: str) -> list[str]:
    try:
        payload = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if item]

