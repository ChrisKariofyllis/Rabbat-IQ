"""Value objects shared by adapters, matching, and the scan pipeline."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GeoPlace:
    postal_code: str
    name: str
    latitude: float
    longitude: float
    country: str


@dataclass
class StoreLocation:
    external_id: str
    name: str
    chain: str
    address: str
    postal_code: str
    city: str
    latitude: float | None
    longitude: float | None
    distance_m: float | None
    opening_hours: str
    source: str


@dataclass
class Flyer:
    external_id: str
    title: str
    chain: str
    industry: str
    valid_from: datetime | None
    valid_to: datetime | None
    page_count: int
    offer_count: int
    cover_url: str
    page_urls: list[str] = field(default_factory=list)
    source_url: str = ""
    source: str = "marktguru"


@dataclass
class Offer:
    external_id: str
    source: str
    product: str
    description: str
    brand: str
    price: float | None
    old_price: float | None
    unit: str
    reference_price: float | None
    chain: str
    store_name: str
    valid_from: datetime | None
    valid_to: datetime | None
    image_url: str
    link_url: str
    leaflet_id: str = ""


@dataclass
class MatchDraft:
    fingerprint: str
    interest: str
    product: str
    description: str
    price: float | None
    original_price: float | None
    discount: str
    store_name: str
    chain: str
    valid_from: datetime | None
    valid_to: datetime | None
    confidence: float
    reason: str
    image_url: str
    link_url: str
    source: str
    external_id: str


@dataclass
class MatchResult:
    drafts: list[MatchDraft]
    note: str = ""
