"""SQLite tables. All shopping data stays in this database."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.formatting import utcnow


class Base(DeclarativeBase):
    pass


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    postal_code: Mapped[str] = mapped_column(String(16), default="")
    country: Mapped[str] = mapped_column(String(2), default="de")
    radius_km: Mapped[float] = mapped_column(Float, default=5)
    place_name: Mapped[str] = mapped_column(String(160), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    scan_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    preferred_stores: Mapped[str] = mapped_column(Text, default="")
    categories: Mapped[str] = mapped_column(Text, default="grocery,drugstore,hardware")
    match_mode: Mapped[str] = mapped_column(String(16), default="keyword")
    min_confidence: Mapped[float] = mapped_column(Float, default=0.55)
    vision_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    vision_max_pages: Mapped[int] = mapped_column(Integer, default=3)
    ai_provider: Mapped[str] = mapped_column(String(32), default="openai")
    ai_model: Mapped[str] = mapped_column(String(80), default="")
    ai_api_key: Mapped[str] = mapped_column(Text, default="")
    ai_base_url: Mapped[str] = mapped_column(String(240), default="http://127.0.0.1:11434")
    telegram_bot_token: Mapped[str] = mapped_column(Text, default="")
    telegram_chat_id: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Interest(Base):
    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_store_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    chain: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(240), default="")
    postal_code: Mapped[str] = mapped_column(String(16), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_hours: Mapped[str] = mapped_column(String(240), default="")
    source: Mapped[str] = mapped_column(String(40), default="marktguru")


class Flyer(Base):
    __tablename__ = "flyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    chain: Mapped[str] = mapped_column(String(120), default="")
    industry: Mapped[str] = mapped_column(String(80), default="")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    offer_count: Mapped[int] = mapped_column(Integer, default=0)
    cover_url: Mapped[str] = mapped_column(Text, default="")
    pages_json: Mapped[str] = mapped_column(Text, default="[]")
    source_url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="marktguru")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(40), default="marktguru")
    product: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(120), default="")
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    old_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40), default="")
    reference_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    chain: Mapped[str] = mapped_column(String(120), default="")
    store_name: Mapped[str] = mapped_column(String(200), default="")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    image_url: Mapped[str] = mapped_column(Text, default="")
    link_url: Mapped[str] = mapped_column(Text, default="")
    leaflet_id: Mapped[str] = mapped_column(String(64), default="")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    interest: Mapped[str] = mapped_column(String(80))
    product: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount: Mapped[str] = mapped_column(String(16), default="")
    store_name: Mapped[str] = mapped_column(String(200), default="")
    chain: Mapped[str] = mapped_column(String(120), default="")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    link_url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="")
    external_id: Mapped[str] = mapped_column(String(120), default="")
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_error: Mapped[str] = mapped_column(Text, default="")
    notify_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stores_found: Mapped[int] = mapped_column(Integer, default=0)
    flyers_found: Mapped[int] = mapped_column(Integer, default=0)
    offers_seen: Mapped[int] = mapped_column(Integer, default=0)
    matches_found: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")


class AiCache(Base):
    __tablename__ = "ai_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
