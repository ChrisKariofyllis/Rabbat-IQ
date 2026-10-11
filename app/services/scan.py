"""One scan: locate the postal code, load offers, match interests, notify."""

import asyncio
import logging
from datetime import timedelta

from app.adapters.marktguru import AdapterError
from app.adapters.registry import build_marktguru, industries_from_settings
from app.ai.glossary import queries_for_interest
from app.ai.matcher import match_offers
from app.domain import Offer
from app.formatting import ensure_utc, utcnow
from app.geo import nominatim_geocode
from app.notifications.telegram import notify_pending
from app.services import repository
from app.textutil import parse_preferred, same_chain

log = logging.getLogger(__name__)

_state = {"running": False, "trigger": ""}


class ScanError(Exception):
    pass


def is_scanning() -> bool:
    return bool(_state["running"])


def reset_scan_state() -> None:
    _state["running"] = False
    _state["trigger"] = ""


def try_start_scan(trigger: str) -> str:
    """Schedule a scan on the running event loop. Call this from async code."""

    if _state["running"]:
        return "busy"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        log.error("scan requested outside the event loop")
        return "busy"
    _state["running"] = True
    _state["trigger"] = trigger

    async def wrapper() -> None:
        try:
            await _execute(trigger)
        except Exception:
            log.exception("background scan failed")
        finally:
            _state["running"] = False
            _state["trigger"] = ""

    loop.create_task(wrapper())
    return "started"


async def run_scan(trigger: str, sources=None, notify=None) -> dict:
    """Run a scan and wait for it. Tests and direct callers use this."""

    if _state["running"]:
        return {"status": "busy"}
    _state["running"] = True
    _state["trigger"] = trigger
    try:
        return await _execute(trigger, sources=sources, notify=notify)
    finally:
        _state["running"] = False
        _state["trigger"] = ""


def scan_status() -> dict:
    settings = repository.get_settings()
    last = repository.latest_scan()
    next_at = None
    ready = bool((settings.postal_code or "").strip()) and bool(repository.list_interests())
    if ready and not _state["running"]:
        interval = max(15, int(settings.scan_interval_minutes or 30))
        if last is not None and last.started_at is not None and last.status != "running":
            started = ensure_utc(last.started_at)
            if started is not None:
                next_at = started + timedelta(minutes=interval)
        elif last is None or last.status != "running":
            next_at = utcnow()
    return {
        "running": _state["running"],
        "trigger": _state["trigger"],
        "next_scan_at": next_at,
        "last": _public_scan(last),
    }


async def _execute(trigger: str, sources=None, notify=None) -> dict:
    scan_id = repository.start_scan(trigger)
    try:
        result = await _scan_body(sources=sources, notify=notify)
    except Exception as exc:
        message = exc.args[0] if isinstance(exc, (ScanError, AdapterError)) else "The scan failed before it finished."
        if not isinstance(exc, (ScanError, AdapterError)):
            log.exception("scan failed")
        repository.finish_scan(scan_id, status="error", message=str(message)[:500])
        return {"status": "error", "message": str(message)}
    repository.finish_scan(scan_id, status="ok", **result)
    return {"status": "ok", **result}


async def _scan_body(sources=None, notify=None) -> dict:
    settings = repository.get_settings()
    postal_code = (settings.postal_code or "").strip()
    if not postal_code:
        raise ScanError("Set a postal code before scanning.")
    interests = [row.text for row in repository.list_interests()]
    if not interests:
        raise ScanError("Add at least one interest before scanning.")

    adapter = (sources or [build_marktguru(settings)])[0]
    async with adapter:
        place = await adapter.geocode(postal_code, settings.country or "de")
        if place is None:
            place = await nominatim_geocode(postal_code, settings.country or "de")
        if place is None:
            raise ScanError("That postal code could not be located.")
        repository.update_settings(
            place_name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
        )
        industries = industries_from_settings(settings)
        preferred = parse_preferred(settings.preferred_stores)
        flyers = await adapter.leaflets(place, industries, preferred)
        stores = await adapter.nearby_stores(place, flyers, float(settings.radius_km) * 1000)
        stores = _dedupe_stores(stores)[:80]
        offers = await _collect_offers(adapter, place, interests, preferred, stores)

    repository.replace_stores(stores)
    repository.replace_flyers(flyers)
    repository.replace_offers(offers)
    matched = await match_offers(offers, interests, settings, flyers, stores)
    saved = repository.save_matches(matched.drafts)
    if notify is None:
        await notify_pending()
    else:
        await notify(saved)
    repository.prune_ai_cache()
    message = (
        f"{len(stores)} stores, {len(flyers)} flyers, {len(offers)} offers, {len(saved)} new matches."
    )
    if matched.note:
        message = f"{message} {matched.note}"
    log.info("scan finished: %s", message)
    return {
        "message": message[:500],
        "stores_found": len(stores),
        "flyers_found": len(flyers),
        "offers_seen": len(offers),
        "matches_found": len(saved),
    }


async def _collect_offers(adapter, place, interests, preferred, stores) -> list[Offer]:
    nearby_chains = [store.chain for store in stores if store.chain]
    found: dict[str, Offer] = {}
    for interest in interests:
        queries = queries_for_interest(interest) or [interest]
        for query in queries:
            batch = await adapter.search_offers(place, query, limit=24)
            _keep_offers(batch, preferred, nearby_chains, found)
            if len(found) >= 200:
                return list(found.values())
    return list(found.values())


def _keep_offers(batch, preferred, nearby_chains, found: dict[str, Offer]) -> None:
    for offer in batch:
        if preferred and not any(same_chain(offer.chain, item) or same_chain(offer.store_name, item) for item in preferred):
            continue
        if nearby_chains and offer.chain and not any(same_chain(offer.chain, chain) for chain in nearby_chains):
            continue
        found.setdefault(offer.external_id or offer.product, offer)


def _dedupe_stores(stores):
    best = {}
    for store in stores:
        key = store.external_id or store.name
        current = best.get(key)
        if current is None or (store.distance_m or 1e18) < (current.distance_m or 1e18):
            best[key] = store
    return sorted(best.values(), key=lambda item: (item.distance_m is None, item.distance_m or 0, item.name))


def _public_scan(row) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "trigger": row.trigger,
        "status": row.status,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "stores_found": row.stores_found,
        "flyers_found": row.flyers_found,
        "offers_seen": row.offers_seen,
        "matches_found": row.matches_found,
        "message": row.message,
    }
