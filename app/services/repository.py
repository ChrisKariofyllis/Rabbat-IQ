"""Read and write the local database.

Callers do not hold sessions. Returned rows are detached and safe to use
after the function returns.
"""

import json

from sqlalchemy import delete, select

from app.config import get_env
from app.db import session_scope
from app.domain import Flyer as FlyerDTO
from app.domain import MatchDraft
from app.domain import Offer as OfferDTO
from app.domain import StoreLocation
from app.formatting import utcnow
from app.models import AiCache, Flyer, Interest, Match, Offer, ScanRun, Settings, Store


def _detach(session, row):
    session.flush()
    session.expunge(row)
    return row


def _ensure_settings(session) -> Settings:
    row = session.get(Settings, 1)
    if row is not None:
        return row
    env = get_env()
    row = Settings(
        id=1,
        postal_code=(env.postal_code or "").strip(),
        country=(env.country or "de").strip().lower() or "de",
        radius_km=5,
        place_name="",
        latitude=None,
        longitude=None,
        scan_interval_minutes=30,
        preferred_stores="",
        categories="grocery,drugstore,hardware",
        match_mode="keyword",
        min_confidence=0.55,
        vision_enabled=False,
        vision_max_pages=3,
        ai_provider="openai",
        ai_model="",
        ai_api_key="",
        ai_base_url="http://127.0.0.1:11434",
        telegram_bot_token="",
        telegram_chat_id="",
        updated_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def get_settings() -> Settings:
    with session_scope() as session:
        return _detach(session, _ensure_settings(session))


def update_settings(**fields) -> Settings:
    with session_scope() as session:
        row = _ensure_settings(session)
        for key, value in fields.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        return _detach(session, row)


def list_interests() -> list[Interest]:
    with session_scope() as session:
        rows = list(session.scalars(select(Interest).order_by(Interest.created_at, Interest.id)))
        for row in rows:
            session.expunge(row)
        return rows


def add_interest(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "empty"
    if len(cleaned) > 80:
        return "long"
    with session_scope() as session:
        rows = list(session.scalars(select(Interest)))
        if any(row.text.casefold() == cleaned.casefold() for row in rows):
            return "duplicate"
        if len(rows) >= 30:
            return "limit"
        session.add(Interest(text=cleaned, created_at=utcnow()))
        return "added"


def delete_interest(interest_id: int) -> bool:
    with session_scope() as session:
        row = session.get(Interest, interest_id)
        if row is None:
            return False
        session.delete(row)
        return True


def delete_interest_text(text: str) -> bool:
    cleaned = " ".join((text or "").split()).casefold()
    if not cleaned:
        return False
    with session_scope() as session:
        rows = list(session.scalars(select(Interest)))
        for row in rows:
            if row.text.casefold() == cleaned:
                session.delete(row)
                return True
        return False


def replace_stores(stores: list[StoreLocation]) -> None:
    with session_scope() as session:
        session.execute(delete(Store))
        for item in stores:
            session.add(
                Store(
                    external_id=item.external_id,
                    name=item.name,
                    chain=item.chain,
                    address=item.address,
                    postal_code=item.postal_code,
                    city=item.city,
                    latitude=item.latitude,
                    longitude=item.longitude,
                    distance_m=item.distance_m,
                    opening_hours=item.opening_hours,
                    source=item.source,
                )
            )


def list_stores() -> list[Store]:
    with session_scope() as session:
        rows = list(session.scalars(select(Store)))
        rows.sort(key=lambda row: (row.distance_m is None, row.distance_m or 0, row.name))
        for row in rows:
            session.expunge(row)
        return rows


def replace_flyers(flyers: list[FlyerDTO]) -> None:
    with session_scope() as session:
        session.execute(delete(Flyer))
        for item in flyers:
            session.add(
                Flyer(
                    external_id=item.external_id,
                    title=item.title,
                    chain=item.chain,
                    industry=item.industry,
                    valid_from=item.valid_from,
                    valid_to=item.valid_to,
                    page_count=item.page_count,
                    offer_count=item.offer_count,
                    cover_url=item.cover_url,
                    pages_json=json.dumps(item.page_urls),
                    source_url=item.source_url,
                    source=item.source,
                    scope=item.scope or "",
                )
            )


def list_flyers() -> list[Flyer]:
    with session_scope() as session:
        rows = list(session.scalars(select(Flyer)))
        rows.sort(
            key=lambda row: (
                0 if (row.scope or "") == "local" else 1,
                -(row.offer_count or 0),
                row.chain or "",
                row.title or "",
            )
        )
        for row in rows:
            session.expunge(row)
        return rows


def get_flyer(flyer_id: int) -> Flyer | None:
    with session_scope() as session:
        row = session.get(Flyer, flyer_id)
        if row is None:
            return None
        return _detach(session, row)


def replace_offers(offers: list[OfferDTO]) -> None:
    with session_scope() as session:
        session.execute(delete(Offer))
        for item in offers:
            session.add(
                Offer(
                    external_id=item.external_id,
                    source=item.source,
                    product=item.product,
                    description=item.description,
                    brand=item.brand,
                    price=item.price,
                    old_price=item.old_price,
                    unit=item.unit,
                    reference_price=item.reference_price,
                    chain=item.chain,
                    store_name=item.store_name,
                    valid_from=item.valid_from,
                    valid_to=item.valid_to,
                    image_url=item.image_url,
                    link_url=item.link_url,
                    leaflet_id=item.leaflet_id,
                )
            )


def list_offers() -> list[Offer]:
    with session_scope() as session:
        rows = list(session.scalars(select(Offer).order_by(Offer.chain, Offer.price)))
        for row in rows:
            session.expunge(row)
        return rows


def save_matches(drafts: list[MatchDraft]) -> list[Match]:
    created: list[Match] = []
    with session_scope() as session:
        for draft in drafts:
            existing = session.scalar(select(Match).where(Match.fingerprint == draft.fingerprint))
            if existing is not None:
                continue
            row = Match(
                fingerprint=draft.fingerprint,
                interest=draft.interest,
                product=draft.product,
                description=draft.description,
                price=draft.price,
                original_price=draft.original_price,
                discount=draft.discount,
                store_name=draft.store_name,
                chain=draft.chain,
                valid_from=draft.valid_from,
                valid_to=draft.valid_to,
                confidence=draft.confidence,
                reason=draft.reason,
                image_url=draft.image_url,
                link_url=draft.link_url,
                source=draft.source,
                external_id=draft.external_id,
                notified_at=None,
                notify_error="",
                notify_attempts=0,
                created_at=utcnow(),
            )
            session.add(row)
            session.flush()
            created.append(row)
        for row in created:
            session.expunge(row)
        return created


def list_matches(limit: int = 100) -> list[Match]:
    with session_scope() as session:
        rows = list(
            session.scalars(select(Match).order_by(Match.created_at.desc(), Match.id.desc()).limit(limit))
        )
        for row in rows:
            session.expunge(row)
        return rows


def count_matches() -> int:
    with session_scope() as session:
        return len(list(session.scalars(select(Match.id))))


def clear_matches() -> None:
    with session_scope() as session:
        session.execute(delete(Match))


def list_pending_matches(limit: int = 15) -> list[Match]:
    with session_scope() as session:
        rows = list(
            session.scalars(
                select(Match)
                .where(Match.notified_at.is_(None), Match.notify_attempts < 3)
                .order_by(Match.created_at.asc())
                .limit(limit)
            )
        )
        for row in rows:
            session.expunge(row)
        return rows


def mark_notified(match_id: int) -> None:
    with session_scope() as session:
        row = session.get(Match, match_id)
        if row is None:
            return
        row.notified_at = utcnow()
        row.notify_error = ""


def mark_notify_failed(match_id: int, message: str) -> None:
    with session_scope() as session:
        row = session.get(Match, match_id)
        if row is None:
            return
        row.notify_attempts += 1
        row.notify_error = message[:300]


def start_scan(trigger: str) -> int:
    with session_scope() as session:
        row = ScanRun(trigger=trigger, status="running", started_at=utcnow(), message="")
        session.add(row)
        session.flush()
        return row.id


def finish_scan(scan_id: int, **fields) -> None:
    with session_scope() as session:
        row = session.get(ScanRun, scan_id)
        if row is None:
            return
        for key, value in fields.items():
            setattr(row, key, value)
        row.finished_at = utcnow()


def latest_scan() -> ScanRun | None:
    with session_scope() as session:
        row = session.scalar(select(ScanRun).order_by(ScanRun.id.desc()).limit(1))
        if row is None:
            return None
        return _detach(session, row)


def fail_stale_scan(minutes: int = 30) -> None:
    from datetime import timedelta

    with session_scope() as session:
        row = session.scalar(select(ScanRun).order_by(ScanRun.id.desc()).limit(1))
        if row is None or row.status != "running" or row.finished_at is not None:
            return
        started = row.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=utcnow().tzinfo)
        if utcnow() - started < timedelta(minutes=minutes):
            return
        row.status = "error"
        row.finished_at = utcnow()
        row.message = "The previous scan did not finish. It was marked failed so a new one can run."


def cache_get(key: str) -> str | None:
    with session_scope() as session:
        row = session.get(AiCache, key)
        if row is None:
            return None
        return row.body


def cache_set(key: str, body: str) -> None:
    with session_scope() as session:
        row = session.get(AiCache, key)
        if row is None:
            session.add(AiCache(cache_key=key, body=body, created_at=utcnow()))
        else:
            row.body = body
            row.created_at = utcnow()


def prune_ai_cache(keep: int = 200) -> None:
    with session_scope() as session:
        rows = list(session.scalars(select(AiCache).order_by(AiCache.created_at.desc())))
        for row in rows[keep:]:
            session.delete(row)
