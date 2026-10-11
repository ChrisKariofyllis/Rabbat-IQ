"""The offer-source interface.

A source turns a postal code into places, leaflets, nearby stores, and offers.
Marktguru is the built-in source. Copy ``chain_template.py`` to add another.
"""

from typing import Protocol

from app.domain import Flyer, GeoPlace, Offer, StoreLocation


class OfferSource(Protocol):
    id: str
    label: str

    async def __aenter__(self) -> "OfferSource": ...

    async def __aexit__(self, exc_type, exc, tb) -> bool: ...

    async def geocode(self, postal_code: str, country: str) -> GeoPlace | None: ...

    async def leaflets(
        self,
        place: GeoPlace,
        industries: set[str] | None,
        preferred: list[str],
    ) -> list[Flyer]: ...

    async def nearby_stores(
        self,
        place: GeoPlace,
        flyers: list[Flyer],
        radius_m: float,
    ) -> list[StoreLocation]: ...

    async def search_offers(self, place: GeoPlace, query: str, limit: int = 24) -> list[Offer]: ...
