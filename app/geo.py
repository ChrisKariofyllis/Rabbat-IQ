"""Postal-code geocoding fallback via Nominatim.

Marktguru's location search is tried first. Nominatim is only used when that
fails. The public Nominatim service asks for a descriptive User-Agent and at
most one request per second, which this fallback respects by being rare.
"""

import logging

import httpx

from app.domain import GeoPlace

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Markthunter/0.1 (personal self-hosted deal scanner)"


async def nominatim_geocode(postal_code: str, country: str) -> GeoPlace | None:
    params = {
        "postalcode": postal_code,
        "country": country or "de",
        "format": "jsonv2",
        "limit": "1",
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(NOMINATIM_URL, params=params, headers=headers)
    except httpx.HTTPError as exc:
        log.warning("nominatim request failed: %s", exc)
        return None
    if response.status_code >= 400:
        log.warning("nominatim returned HTTP %s", response.status_code)
        return None
    payload = response.json()
    if not payload:
        return None
    item = payload[0]
    try:
        latitude = float(item["lat"])
        longitude = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    name = str(item.get("display_name") or postal_code).split(",")[0].strip()
    return GeoPlace(
        postal_code=postal_code,
        name=name or postal_code,
        latitude=latitude,
        longitude=longitude,
        country=country or "de",
    )
