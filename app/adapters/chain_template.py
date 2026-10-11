"""Template for a direct supermarket-site adapter.

Copy this file, rename the class, and register it from
``app/adapters/registry.py``. Keep the new adapter polite:

- Identify the process with a clear User-Agent.
- Wait between requests. One request every few hundred milliseconds is a
  reasonable start; slow down if the site asks you to.
- Read robots.txt and the site's terms before you fetch anything.
- Do not bypass logins, paywalls, or other access controls.
- Cache responses and skip work you already did in this scan.

The class below is not registered, so scans do not call it.
"""

import logging

from app.domain import Flyer, GeoPlace, Offer, StoreLocation

log = logging.getLogger(__name__)


class ChainTemplateAdapter:
    """Skeleton of a chain-specific source. Returns nothing until you fill it in."""

    id = "chain_template"
    label = "Example chain scraper"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def geocode(self, postal_code: str, country: str) -> GeoPlace | None:
        return None

    async def leaflets(self, place, industries, preferred) -> list[Flyer]:
        log.debug("chain template leaflets() is not implemented")
        return []

    async def nearby_stores(self, place, flyers, radius_m: float) -> list[StoreLocation]:
        return []

    async def search_offers(self, place, query: str, limit: int = 24) -> list[Offer]:
        return []
