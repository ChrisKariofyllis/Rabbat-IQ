"""Postal-code geocoding fallback and OpenStreetMap branch lookup.

Marktguru's location search is tried first. Nominatim is only used when that
fails. The public Nominatim service asks for a descriptive User-Agent and at
most one request per second, which this fallback respects by being rare.

Supermarket branches that a leaflet does not list are read from OpenStreetMap
through Overpass, around the same postal-code center.
"""

import asyncio
import logging
import math

import httpx

from app.domain import GeoPlace, StoreLocation

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Rabbat-IQ/0.1 (personal self-hosted deal scanner)"
OVERPASS_URLS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)


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


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1, math.sqrt(arc)))


def stores_from_overpass(payload: dict, latitude: float, longitude: float, radius_m: float) -> list[StoreLocation]:
    """Turn an Overpass supermarket answer into branches inside the radius."""

    stores: list[StoreLocation] = []
    for element in payload.get("elements") or []:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") or {}
        point = element.get("center") if element.get("type") == "way" else element
        point = point or {}
        try:
            store_lat = float(point.get("lat"))
            store_lon = float(point.get("lon"))
        except (TypeError, ValueError):
            continue
        distance = haversine_m(latitude, longitude, store_lat, store_lon)
        if distance > radius_m:
            continue
        name = str(tags.get("name") or tags.get("brand") or "").strip()
        if not name:
            continue
        chain = str(tags.get("brand") or name).strip()
        street = " ".join(
            part
            for part in (str(tags.get("addr:street") or "").strip(), str(tags.get("addr:housenumber") or "").strip())
            if part
        )
        element_id = element.get("id")
        element_type = element.get("type") or "node"
        stores.append(
            StoreLocation(
                external_id=f"osm-{element_type}-{element_id}",
                name=name,
                chain=chain,
                address=street,
                postal_code=str(tags.get("addr:postcode") or ""),
                city=str(tags.get("addr:city") or tags.get("addr:suburb") or ""),
                latitude=store_lat,
                longitude=store_lon,
                distance_m=distance,
                opening_hours=str(tags.get("opening_hours") or ""),
                source="openstreetmap",
            )
        )
    return stores


# Chains a leaflet often omits for a small town. Used only when Overpass is down.
_FALLBACK_CHAINS = ("EDEKA", "Netto", "NORMA", "REWE", "Lidl", "ALDI", "PENNY")


def stores_from_nominatim(
    items: list,
    chain: str,
    latitude: float,
    longitude: float,
    radius_m: float,
) -> list[StoreLocation]:
    stores: list[StoreLocation] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        display = str(item.get("display_name") or "")
        address = item.get("address") if isinstance(item.get("address"), dict) else {}
        label = " ".join(
            [
                display,
                str(address.get("shop") or ""),
                str(address.get("name") or ""),
            ]
        )
        if chain.casefold() not in label.casefold():
            continue
        try:
            store_lat = float(item["lat"])
            store_lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        distance = haversine_m(latitude, longitude, store_lat, store_lon)
        if distance > radius_m:
            continue
        street = " ".join(
            part
            for part in (
                str(address.get("road") or "").strip(),
                str(address.get("house_number") or "").strip(),
            )
            if part
        )
        name = str(address.get("shop") or address.get("name") or chain).strip() or chain
        stores.append(
            StoreLocation(
                external_id=f"nominatim-{item.get('osm_type') or 'n'}-{item.get('osm_id') or name}",
                name=name,
                chain=chain,
                address=street,
                postal_code=str(address.get("postcode") or ""),
                city=str(address.get("town") or address.get("village") or address.get("city") or ""),
                latitude=store_lat,
                longitude=store_lon,
                distance_m=distance,
                opening_hours="",
                source="openstreetmap",
            )
        )
    return stores


async def osm_supermarkets(
    latitude: float,
    longitude: float,
    radius_m: float,
    client: httpx.AsyncClient | None = None,
    place_name: str = "",
    country: str = "de",
) -> list[StoreLocation]:
    """Supermarkets OpenStreetMap knows within the radius.

    Overpass is asked first. When it is down, each common chain is looked up
    by name in the town so a missing leaflet branch is still found.
    """

    radius = int(max(200, min(radius_m, 20_000)))
    query = (
        "[out:json][timeout:20];"
        "("
        f'node["shop"="supermarket"](around:{radius},{latitude},{longitude});'
        f'way["shop"="supermarket"](around:{radius},{latitude},{longitude});'
        ");"
        "out center tags;"
    )
    owned = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=25, headers={"User-Agent": USER_AGENT})
    try:
        for url in OVERPASS_URLS:
            try:
                response = await client.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT})
            except httpx.HTTPError as exc:
                log.warning("overpass request failed: %s", exc)
                continue
            if response.status_code >= 400:
                log.warning("overpass returned HTTP %s", response.status_code)
                continue
            try:
                payload = response.json()
            except ValueError:
                continue
            if isinstance(payload, dict):
                found = stores_from_overpass(payload, latitude, longitude, radius_m)
                if found:
                    return found
        if place_name:
            return await _nominatim_chains(client, latitude, longitude, radius_m, place_name, country)
    finally:
        if owned:
            await client.aclose()
    return []


async def _nominatim_chains(client, latitude, longitude, radius_m, place_name, country) -> list[StoreLocation]:
    found: list[StoreLocation] = []
    country_code = (country or "de").lower()
    for index, chain in enumerate(_FALLBACK_CHAINS):
        if index:
            await asyncio.sleep(1.1)
        try:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": f"{chain} {place_name}",
                    "format": "jsonv2",
                    "limit": "3",
                    "addressdetails": "1",
                    "countrycodes": country_code,
                },
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            log.warning("nominatim store search failed: %s", exc)
            continue
        if response.status_code >= 400:
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        if isinstance(payload, list):
            found.extend(stores_from_nominatim(payload, chain, latitude, longitude, radius_m))
    return found
