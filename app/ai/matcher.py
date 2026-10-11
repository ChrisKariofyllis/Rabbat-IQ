"""Turn offers and flyer pages into match drafts.

Keyword mode runs locally. Semantic mode asks the configured model to confirm
matches and to catch products that are the same item in another language.
Vision mode sends a limited number of flyer cover images.
"""

import hashlib
import json
import logging

import httpx

from app.ai.keyword import keyword_matches, nearest_store
from app.ai.providers import AIError, ai_configured, complete
from app.domain import Flyer, MatchDraft, MatchResult, Offer, StoreLocation
from app.fingerprint import fingerprint
from app.formatting import discount_label, format_date
from app.services import repository
from app.textutil import clamp_confidence, extract_json, normalize, parse_price

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You match supermarket offers and flyer pages to a household's shopping interests.
Flyers may be in any language, including German, Greek, and English.
Match exact keywords and clear equivalents, for example "Greek yogurt" matches "Griechischer Joghurt".
Return only JSON with this shape:
{"matches":[{"interest":"","offer_id":"","product":"","price":"","original_price":"","discount":"","store":"","valid_from":"","valid_to":"","confidence":0.0,"reason":""}]}
confidence is a number from 0 to 1.
Include a match only when it really fits an interest.
If nothing matches, return {"matches":[]}.
Do not invent products that are not in the input or on the page.
"""


def _cache_key(prefix: str, payload: str) -> str:
    return hashlib.sha256(f"{prefix}|{payload}".encode("utf-8")).hexdigest()


def _settings_ready(settings) -> bool:
    return ai_configured(settings.ai_provider, settings.ai_api_key, settings.ai_base_url)


async def match_offers(
    offers: list[Offer],
    interests: list[str],
    settings,
    flyers: list[Flyer],
    stores: list[StoreLocation],
    complete_fn=None,
) -> MatchResult:
    caller = complete_fn or _complete_with_settings
    keyword = keyword_matches(offers, interests, stores, settings.min_confidence)
    note = ""
    if settings.match_mode != "semantic" or not _settings_ready(settings):
        drafts = keyword
        if settings.match_mode == "semantic" and not _settings_ready(settings):
            note = "Semantic matching needs an AI key, so keyword matches were used."
    else:
        try:
            drafts = await _semantic(offers, interests, settings, stores, caller)
        except (AIError, ValueError) as exc:
            log.warning("semantic matching failed: %s", exc)
            drafts = keyword
            note = "Semantic matching was unavailable, so keyword matches were used."
    if settings.vision_enabled and _settings_ready(settings) and settings.vision_max_pages > 0:
        try:
            vision = await _vision(flyers, interests, settings, caller)
            drafts = _merge(drafts, vision)
        except (AIError, ValueError) as exc:
            log.warning("vision matching failed: %s", exc)
            extra = "Flyer vision could not be completed."
            note = f"{note} {extra}".strip()
    kept = [draft for draft in drafts if draft.confidence >= settings.min_confidence]
    return MatchResult(drafts=kept, note=note)


async def _complete_with_settings(settings, system: str, user_text: str, images: list[bytes] | None = None) -> str:
    return await complete(
        provider=settings.ai_provider,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        system=system,
        user_text=user_text,
        images=images,
    )


def _merge(primary: list[MatchDraft], extra: list[MatchDraft]) -> list[MatchDraft]:
    seen = {draft.fingerprint for draft in primary}
    merged = list(primary)
    for draft in extra:
        if draft.fingerprint in seen:
            continue
        seen.add(draft.fingerprint)
        merged.append(draft)
    return merged


def _offer_line(offer: Offer) -> str:
    description = (offer.description or "").replace("\n", " ")[:180]
    return " | ".join(
        [
            offer.external_id,
            offer.product,
            offer.brand,
            description,
            "" if offer.price is None else str(offer.price),
            "" if offer.old_price is None else str(offer.old_price),
            offer.chain,
            format_date(offer.valid_from),
            format_date(offer.valid_to),
        ]
    )


async def _semantic(offers, interests, settings, stores, caller) -> list[MatchDraft]:
    drafts: list[MatchDraft] = []
    for start in range(0, len(offers), 25):
        batch = offers[start : start + 25]
        if not batch:
            continue
        user = _semantic_prompt(batch, interests)
        raw = await _cached_complete(settings, user, None, caller)
        drafts.extend(_drafts_from_model(raw, interests, batch, stores, settings.min_confidence))
    return drafts


def _semantic_prompt(offers: list[Offer], interests: list[str]) -> str:
    lines = "\n".join(_offer_line(offer) for offer in offers)
    interest_text = ", ".join(interests)
    return (
        f"Interests: {interest_text}\n"
        "Each offer line is: id | product | brand | description | price | old price | store | valid from | valid to\n"
        f"{lines}"
    )


async def _vision(flyers, interests, settings, caller) -> list[MatchDraft]:
    budget = max(0, min(int(settings.vision_max_pages or 0), 8))
    drafts: list[MatchDraft] = []
    used = 0
    for flyer in flyers:
        if used >= budget:
            break
        if not flyer.page_urls:
            continue
        image = await _download_image(flyer.page_urls[0])
        if not image:
            continue
        user = (
            f"Interests: {', '.join(interests)}\n"
            f"Store: {flyer.chain}\n"
            f"Leaflet validity: {format_date(flyer.valid_from)} to {format_date(flyer.valid_to)}\n"
            "Read this flyer page. Return only products that match an interest. "
            "Leave offer_id empty. Put the interest name in the interest field."
        )
        raw = await _cached_complete(settings, user + f"\nimage:{flyer.page_urls[0]}", image, caller)
        drafts.extend(_vision_drafts(raw, interests, flyer, settings.min_confidence))
        used += 1
    return drafts


async def _cached_complete(settings, user_text: str, image: bytes | None, caller) -> str:
    prefix = "|".join(
        [
            settings.ai_provider,
            settings.ai_model or "",
            hashlib.sha256((settings.ai_api_key or "").encode()).hexdigest()[:8],
        ]
    )
    image_mark = hashlib.sha256(image).hexdigest() if image else ""
    key = _cache_key(prefix, user_text + image_mark)
    cached = repository.cache_get(key)
    if cached:
        return cached
    raw = await caller(settings, SYSTEM_PROMPT, user_text, [image] if image else None)
    repository.cache_set(key, raw)
    return raw


def _drafts_from_model(raw: str, interests, offers, stores, min_confidence: float) -> list[MatchDraft]:
    by_id = {offer.external_id: offer for offer in offers}
    drafts: list[MatchDraft] = []
    for item in _match_items(raw):
        offer = by_id.get(str(item.get("offer_id") or "").strip())
        if offer is None:
            continue
        interest = _resolve_interest(str(item.get("interest") or ""), interests)
        if interest is None:
            continue
        confidence = clamp_confidence(item.get("confidence"))
        if confidence < min_confidence:
            continue
        price = offer.price if offer.price is not None else parse_price(item.get("price"))
        old = offer.old_price if offer.old_price is not None else parse_price(item.get("original_price"))
        reason = str(item.get("reason") or "Matched by the model.").strip()
        drafts.append(
            _draft(
                offer_source=offer.source,
                external_id=offer.external_id,
                interest=interest,
                product=offer.product or str(item.get("product") or "Offer"),
                description=offer.description or "",
                price=price,
                old_price=old,
                chain=offer.chain,
                store_name=str(item.get("store") or "") or nearest_store(stores, offer.chain),
                valid_from=offer.valid_from,
                valid_to=offer.valid_to,
                confidence=confidence,
                reason=reason,
                image_url=offer.image_url,
                link_url=offer.link_url,
            )
        )
    return drafts


def _vision_drafts(raw: str, interests, flyer: Flyer, min_confidence: float) -> list[MatchDraft]:
    drafts: list[MatchDraft] = []
    for item in _match_items(raw):
        interest = _resolve_interest(str(item.get("interest") or ""), interests)
        if interest is None and len(interests) == 1:
            interest = interests[0]
        if interest is None:
            continue
        product = str(item.get("product") or "").strip()
        if not product:
            continue
        confidence = clamp_confidence(item.get("confidence"))
        if confidence < min_confidence:
            continue
        price = parse_price(item.get("price"))
        old = parse_price(item.get("original_price"))
        external_id = f"vision:{flyer.external_id}:{normalize(product)[:40]}"
        drafts.append(
            _draft(
                offer_source="vision",
                external_id=external_id,
                interest=interest,
                product=product,
                description="",
                price=price,
                old_price=old,
                chain=flyer.chain,
                store_name=str(item.get("store") or flyer.chain),
                valid_from=flyer.valid_from,
                valid_to=flyer.valid_to,
                confidence=confidence,
                reason=str(item.get("reason") or "Read from the flyer page.").strip(),
                image_url=flyer.cover_url,
                link_url=flyer.source_url,
                discount=str(item.get("discount") or ""),
            )
        )
    return drafts


def _draft(**kwargs) -> MatchDraft:
    discount = kwargs.pop("discount", None)
    price = kwargs["price"]
    old_price = kwargs["old_price"]
    return MatchDraft(
        fingerprint=fingerprint(
            source=kwargs["offer_source"],
            external_id=kwargs["external_id"],
            interest=kwargs["interest"],
            price=price,
            valid_to=kwargs["valid_to"],
        ),
        interest=kwargs["interest"],
        product=kwargs["product"],
        description=kwargs["description"],
        price=price,
        original_price=old_price,
        discount=discount or discount_label(price, old_price),
        store_name=kwargs["store_name"],
        chain=kwargs["chain"],
        valid_from=kwargs["valid_from"],
        valid_to=kwargs["valid_to"],
        confidence=kwargs["confidence"],
        reason=kwargs["reason"],
        image_url=kwargs["image_url"],
        link_url=kwargs["link_url"],
        source=kwargs["offer_source"],
        external_id=kwargs["external_id"],
    )


def _match_items(raw: str) -> list[dict]:
    parsed = extract_json(raw)
    if isinstance(parsed, list):
        parsed = {"matches": parsed}
    matches = parsed.get("matches") if isinstance(parsed, dict) else None
    if not isinstance(matches, list):
        return []
    return [item for item in matches if isinstance(item, dict)]


def _resolve_interest(label: str, interests: list[str]) -> str | None:
    folded = label.casefold().strip()
    if not folded:
        return interests[0] if len(interests) == 1 else None
    for interest in interests:
        if interest.casefold().strip() == folded:
            return interest
    for interest in interests:
        name = interest.casefold().strip()
        if name and (name in folded or folded in name):
            return interest
    return None


async def _download_image(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Rabbat-IQ/0.1"})
    except httpx.HTTPError:
        log.warning("could not download flyer image")
        return None
    if response.status_code >= 400:
        return None
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".webp", ".png")):
        return None
    if len(response.content) > 2_000_000:
        log.info("skipping flyer image larger than 2 MB")
        return None
    return response.content


def explain_matches_json(raw: str) -> str:
    """Used by the settings connection test. Returns a short status."""

    parsed = extract_json(raw)
    if isinstance(parsed, dict) and parsed.get("ok") is True:
        return "The model replied."
    return "The model replied, but not with the expected JSON."
