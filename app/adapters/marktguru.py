"""Marktguru adapter for Germany (marktguru.de) and Austria (marktguru.at).

This is an unofficial client. It calls the same public JSON API the Marktguru
website uses. Keys can be supplied with RABBAT_IQ_MARKTGURU_API_KEY and
RABBAT_IQ_MARKTGURU_CLIENT_KEY. When they are empty, the adapter reads the
keys embedded in the public homepage and caches them under the data directory.

You are responsible for complying with Marktguru's terms of use.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from urllib.parse import quote_plus

import httpx

from app.domain import Flyer, GeoPlace, Offer, StoreLocation
from app.formatting import parse_dt
from app.textutil import same_chain

log = logging.getLogger(__name__)

USER_AGENT = "Rabbat-IQ/0.1 (personal self-hosted deal scanner)"
KEY_TTL_SECONDS = 12 * 60 * 60

HOSTS = {
    "de": {
        "site": "https://www.marktguru.de",
        "api": "https://api.marktguru.de/api/v1",
        "cdn": "https://cdn.marktguru.de",
    },
    "at": {
        "site": "https://www.marktguru.at",
        "api": "https://api.marktguru.at/api/v1",
        "cdn": "https://cdn.marktguru.at",
    },
}

GROCERY = {
    "Supermarkt",
    "Discounter",
    "Biomarkt",
    "Getränkemarkt",
    "Essen & Genießen",
}
DRUGSTORE = {"Drogerie & Gesundheit"}
HARDWARE = {"Baumarkt"}


class AdapterError(Exception):
    """A source could not complete a request. The message is safe to show."""


def selected_industries(categories: list[str] | set[str] | None) -> set[str] | None:
    chosen = {item.strip() for item in (categories or []) if item and item.strip()}
    if not chosen or "all" in chosen:
        return None if "all" in chosen else set(GROCERY)
    names: set[str] = set()
    if "grocery" in chosen:
        names |= GROCERY
    if "drugstore" in chosen:
        names |= DRUGSTORE
    if "hardware" in chosen:
        names |= HARDWARE
    return names or set(GROCERY)


def keep_flyer(
    industry: str,
    chain: str,
    industries: set[str] | None,
    preferred: list[str],
) -> bool:
    if industries is not None and industry not in industries:
        return False
    if preferred and not any(same_chain(chain, item) for item in preferred):
        return False
    return True


def parse_homepage_keys(html: str) -> tuple[str, str]:
    import re

    for blob in re.findall(r'<script type="application/json">(.*?)</script>', html, flags=re.S):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        config = data.get("config") if isinstance(data, dict) else None
        if isinstance(config, dict) and config.get("apiKey"):
            return str(config["apiKey"]), str(config.get("clientKey") or "")
    raise AdapterError(
        "Could not read Marktguru API keys from the public homepage. "
        "Set RABBAT_IQ_MARKTGURU_API_KEY and RABBAT_IQ_MARKTGURU_CLIENT_KEY."
    )


def offer_image_url(cdn: str, offer_id, size: str = "medium") -> str:
    return f"{cdn}/api/v1/offers/{offer_id}/images/default/0/{size}.jpg"


def leaflet_page_url(cdn: str, leaflet_id, page: int, size: str = "small") -> str:
    return f"{cdn}/api/v1/leaflets/{leaflet_id}/images/pages/{page}/{size}.jpg"


def _first(items):
    if isinstance(items, list) and items:
        return items[0] or {}
    return {}


def parse_offer(raw: dict, *, cdn: str, site: str) -> Offer:
    product = raw.get("product") or {}
    brand = raw.get("brand") or {}
    advertiser = _first(raw.get("advertisers"))
    validity = _first(raw.get("validityDates"))
    unit = raw.get("unit") or {}
    offer_id = str(raw.get("id") or "")
    chain = str(advertiser.get("name") or "")
    product_name = str(product.get("name") or raw.get("description") or "Offer")
    external = str(raw.get("externalUrl") or "")
    link = external or f"{site}/suche?q={quote_plus(product_name)}"
    leaflet_id = raw.get("leafletFlightId")
    return Offer(
        external_id=offer_id,
        source="marktguru",
        product=product_name,
        description=str(raw.get("description") or ""),
        brand=str(brand.get("name") or ""),
        price=_number(raw.get("price")),
        old_price=_number(raw.get("oldPrice")),
        unit=str(unit.get("shortName") or ""),
        reference_price=_number(raw.get("referencePrice")),
        chain=chain,
        store_name=chain,
        valid_from=parse_dt(validity.get("from")),
        valid_to=parse_dt(validity.get("to")),
        image_url=offer_image_url(cdn, offer_id) if offer_id else "",
        link_url=link,
        leaflet_id="" if leaflet_id is None else str(leaflet_id),
    )


def parse_store(raw: dict) -> StoreLocation:
    location = raw.get("location") or {}
    hours = raw.get("openingHours") or {}
    zips = location.get("zipCodes") or []
    latitude = _number(location.get("latitude"))
    longitude = _number(location.get("longitude"))
    return StoreLocation(
        external_id=str(raw.get("id") or ""),
        name=str(raw.get("name") or "Store"),
        chain=str(raw.get("storeChainName") or ""),
        address=str(location.get("address") or ""),
        postal_code=str(zips[0]) if zips else "",
        city=str(location.get("name") or ""),
        latitude=latitude,
        longitude=longitude,
        distance_m=_number(raw.get("distanceInMeters")),
        opening_hours=str(hours.get("displayText") or hours.get("specification") or ""),
        source="marktguru",
    )


def parse_flight(raw: dict, *, cdn: str, site: str) -> Flyer:
    advertiser = raw.get("advertiser") or {}
    industry = raw.get("industry") or {}
    leaflet_id = str(raw.get("mainLeafletId") or raw.get("id") or "")
    page_count = int(raw.get("pageCount") or 0)
    preview_pages = max(1, min(page_count or 1, 6))
    start_index = int(raw.get("mainLeafletPageIndex") or 0)
    page_urls = [
        leaflet_page_url(cdn, leaflet_id, start_index + offset)
        for offset in range(preview_pages)
        if leaflet_id
    ]
    chain = str(advertiser.get("name") or "Leaflet")
    return Flyer(
        external_id=leaflet_id,
        title=chain,
        chain=chain,
        industry=str(industry.get("name") or ""),
        valid_from=parse_dt(raw.get("validFrom")),
        valid_to=parse_dt(raw.get("validTo")),
        page_count=page_count,
        offer_count=int(raw.get("offerCount") or 0),
        cover_url=page_urls[0] if page_urls else "",
        page_urls=page_urls,
        source_url=f"{site}/leaflets/{leaflet_id}/page/0" if leaflet_id else site,
        source="marktguru",
    )


def parse_place(raw: dict, postal_code: str, country: str) -> GeoPlace | None:
    zips = [str(item) for item in raw.get("zipCodes") or []]
    try:
        latitude = float(raw.get("latitude"))
        longitude = float(raw.get("longitude"))
    except (TypeError, ValueError):
        return None
    return GeoPlace(
        postal_code=postal_code or (zips[0] if zips else ""),
        name=str(raw.get("name") or postal_code),
        latitude=latitude,
        longitude=longitude,
        country=country,
    )


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class MarktguruAdapter:
    id = "marktguru"
    label = "Marktguru"

    def __init__(
        self,
        *,
        country: str = "de",
        api_key: str = "",
        client_key: str = "",
        data_dir: str = "./data",
        client: httpx.AsyncClient | None = None,
        delay: float = 0.3,
    ):
        self.country = country if country in HOSTS else "de"
        hosts = HOSTS[self.country]
        self.site = hosts["site"]
        self.api_base = hosts["api"]
        self.cdn = hosts["cdn"]
        self.api_key = (api_key or "").strip()
        self.client_key = (client_key or "").strip()
        self.data_dir = Path(data_dir)
        self.delay = delay
        self._client = client
        self._owned: httpx.AsyncClient | None = None
        self._last = 0.0
        self._pace = asyncio.Lock()

    async def __aenter__(self):
        if self._client is None:
            self._owned = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT})
            self._client = self._owned
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._owned is not None:
            await self._owned.aclose()
            self._owned = None
            self._client = None
        return False

    async def geocode(self, postal_code: str, country: str) -> GeoPlace | None:
        data = await self._get("locations", {"q": postal_code, "limit": 5})
        results = data.get("results") or []
        for item in results:
            zips = [str(code) for code in item.get("zipCodes") or []]
            if postal_code in zips:
                place = parse_place(item, postal_code, country or self.country)
                if place is not None:
                    return place
        for item in results:
            place = parse_place(item, postal_code, country or self.country)
            if place is not None:
                return place
        return None

    async def leaflets(self, place: GeoPlace, industries: set[str] | None, preferred: list[str]) -> list[Flyer]:
        data = await self._get(
            "leafletFlights",
            {
                "as": "web",
                "zipCode": place.postal_code,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "limit": 100,
                "offset": 0,
            },
        )
        flyers: list[Flyer] = []
        for item in data.get("results") or []:
            flyer = parse_flight(item, cdn=self.cdn, site=self.site)
            if not keep_flyer(flyer.industry, flyer.chain, industries, preferred):
                continue
            flyers.append(flyer)
        flyers.sort(key=lambda flyer: flyer.offer_count, reverse=True)
        deduped: list[Flyer] = []
        seen: set[str] = set()
        for flyer in flyers:
            if flyer.external_id in seen:
                continue
            seen.add(flyer.external_id)
            deduped.append(flyer)
        return deduped[:30]

    async def nearby_stores(self, place: GeoPlace, flyers: list[Flyer], radius_m: float) -> list[StoreLocation]:
        by_chain: dict[str, Flyer] = {}
        for flyer in flyers:
            current = by_chain.get(flyer.chain)
            if current is None or flyer.offer_count > current.offer_count:
                by_chain[flyer.chain] = flyer
        found: list[StoreLocation] = []
        for flyer in list(by_chain.values())[:12]:
            if not flyer.external_id:
                continue
            try:
                data = await self._get(
                    f"leaflets/{flyer.external_id}/stores",
                    {
                        "limit": 20,
                        "zipCode": place.postal_code,
                        "latitude": place.latitude,
                        "longitude": place.longitude,
                    },
                )
            except AdapterError as exc:
                log.warning("store lookup for %s failed: %s", flyer.chain, exc)
                continue
            for item in data.get("results") or []:
                store = parse_store(item)
                if store.distance_m is None or store.distance_m <= radius_m:
                    found.append(store)
        return found

    async def search_offers(self, place: GeoPlace, query: str, limit: int = 24) -> list[Offer]:
        data = await self._get(
            "offers/search",
            {
                "as": "web",
                "q": query,
                "zipCode": place.postal_code,
                "limit": max(1, min(limit, 50)),
                "offset": 0,
            },
        )
        offers = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            offers.append(parse_offer(item, cdn=self.cdn, site=self.site))
        return offers

    async def _keys(self) -> tuple[str, str]:
        if self.api_key:
            return self.api_key, self.client_key
        cached = self._read_cache()
        if cached:
            return cached
        html = await self._homepage()
        api_key, client_key = parse_homepage_keys(html)
        self._write_cache(api_key, client_key)
        self.api_key = api_key
        self.client_key = client_key
        return api_key, client_key

    async def _homepage(self) -> str:
        await self._pause()
        client = self._client
        close = False
        if client is None:
            client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT})
            close = True
        try:
            response = await client.get(f"{self.site}/", headers={"Accept": "text/html", "User-Agent": USER_AGENT})
        finally:
            if close:
                await client.aclose()
        if response.status_code >= 400:
            raise AdapterError(f"Marktguru homepage returned HTTP {response.status_code}.")
        return response.text

    async def _get(self, path: str, params: dict) -> dict:
        await self._pause()
        api_key, client_key = await self._keys()
        headers = {"x-apikey": api_key, "Accept": "application/json", "User-Agent": USER_AGENT}
        if client_key:
            headers["x-clientkey"] = client_key
        url = f"{self.api_base}/{path.lstrip('/')}"
        client = self._client
        close = False
        if client is None:
            client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT})
            close = True
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise AdapterError(f"Could not reach Marktguru ({path}).") from exc
        finally:
            if close:
                await client.aclose()
        if response.status_code == 429:
            raise AdapterError("Marktguru rate limited this request. The next scan will try again.")
        if response.status_code >= 400:
            raise AdapterError(f"Marktguru returned HTTP {response.status_code} while loading {path}.")
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise AdapterError(f"Marktguru returned an unreadable response for {path}.") from exc
        if not isinstance(payload, dict):
            raise AdapterError(f"Marktguru returned an unexpected response for {path}.")
        return payload

    async def _pause(self) -> None:
        if self.delay <= 0:
            return
        async with self._pace:
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    def _cache_path(self) -> Path:
        return self.data_dir / f"marktguru-keys-{self.country}.json"

    def _read_cache(self) -> tuple[str, str] | None:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            fetched = float(payload.get("fetched_at") or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
        if time.time() - fetched > KEY_TTL_SECONDS:
            return None
        api_key = str(payload.get("api_key") or "")
        if not api_key or payload.get("country") != self.country:
            return None
        return api_key, str(payload.get("client_key") or "")

    def _write_cache(self, api_key: str, client_key: str) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path()
            path.write_text(
                json.dumps(
                    {
                        "country": self.country,
                        "api_key": api_key,
                        "client_key": client_key,
                        "fetched_at": time.time(),
                    }
                ),
                encoding="utf-8",
            )
            path.chmod(0o600)
        except OSError:
            log.warning("could not cache Marktguru keys")
