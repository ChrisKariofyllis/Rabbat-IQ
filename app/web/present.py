"""Turn database rows into template-friendly dictionaries."""

import json

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

PALETTE = ("#1e6a43", "#b42318", "#1d4e89", "#8a5a00", "#5c3d8f", "#0f6e6e", "#9a3d6a")

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
        "link_url": getattr(offer, "link_url", "") or "",
        "unit": getattr(offer, "unit", "") or "",
        "reference_price": format_euro(reference) if reference else "",
    }


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
    plotted = [store for store in stores if store.latitude is not None and store.longitude is not None]
    home_lat = None if not home else home[0]
    home_lon = None if not home else home[1]
    coords = [(store.latitude, store.longitude) for store in plotted]
    if home_lat is not None and home_lon is not None:
        coords.append((home_lat, home_lon))
    if not coords:
        plain = [_store_dict(store, None, None, False) for store in stores]
        return plain, None
    lats = [item[0] for item in coords]
    lons = [item[1] for item in coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    lat_pad = max(max_lat - min_lat, 0.01) * 0.15
    lon_pad = max(max_lon - min_lon, 0.01) * 0.15
    min_lat -= lat_pad
    max_lat += lat_pad
    min_lon -= lon_pad
    max_lon += lon_pad
    lat_span = max_lat - min_lat or 0.01
    lon_span = max_lon - min_lon or 0.01

    def xy(lat: float, lon: float) -> tuple[float, float]:
        x = 10 + (lon - min_lon) / lon_span * 80
        y = 10 + (max_lat - lat) / lat_span * 80
        return round(x, 2), round(y, 2)

    views = []
    labels_left = 5
    for store in stores:
        point = None
        show = False
        if store.latitude is not None and store.longitude is not None:
            point = xy(store.latitude, store.longitude)
            show = labels_left > 0
            if show:
                labels_left -= 1
        views.append(_store_dict(store, point, _color(store.chain or store.name), show))
    home_point = None
    if home_lat is not None and home_lon is not None:
        hx, hy = xy(home_lat, home_lon)
        home_point = {"x": hx, "y": hy}
    return views, home_point


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


def _store_dict(store, point, color, show_label: bool) -> dict:
    return {
        "name": store.name,
        "chain": store.chain or "",
        "address": store.address or "",
        "city": store.city or "",
        "postal_code": store.postal_code or "",
        "distance": format_distance(store.distance_m),
        "hours": store.opening_hours or "",
        "x": None if point is None else point[0],
        "y": None if point is None else point[1],
        "color": color or "#1e6a43",
        "show_label": show_label,
    }


def _pages(raw: str) -> list[str]:
    try:
        payload = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if item]


def _color(name: str) -> str:
    total = sum(ord(char) for char in name or "")
    return PALETTE[total % len(PALETTE)]
