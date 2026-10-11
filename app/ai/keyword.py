"""Local matcher. It does not call a model."""

from app.ai.glossary import SYNONYMS
from app.domain import MatchDraft, Offer, StoreLocation
from app.fingerprint import fingerprint
from app.formatting import discount_label
from app.textutil import normalize, same_chain


def offer_words(offer: Offer) -> list[str]:
    text = " ".join(
        [
            offer.product or "",
            offer.brand or "",
            offer.description or "",
            offer.chain or "",
            offer.store_name or "",
        ]
    )
    return normalize(text).split()


def word_matches(hay_words: list[str], needle: str) -> bool:
    for word in hay_words:
        if word == needle:
            return True
        if len(needle) >= 5 and (word.startswith(needle) or needle.startswith(word)):
            return True
    return False


def token_satisfied(hay_words: list[str], token: str) -> bool:
    if word_matches(hay_words, token):
        return True
    for synonym in SYNONYMS.get(token, []):
        folded = normalize(synonym)
        if folded and word_matches(hay_words, folded):
            return True
    return False


def score_interest(hay_words: list[str], interest: str) -> tuple[float, str] | None:
    phrase = normalize(interest)
    if not phrase or not hay_words:
        return None
    hay = " ".join(hay_words)
    if " " in phrase and phrase in hay:
        return 0.94, f"The offer text contains “{interest}”."
    required = [token for token in phrase.split() if len(token) >= 3 or token.isdigit()]
    if not required:
        if word_matches(hay_words, phrase):
            return 0.9, f"Matched your interest “{interest}”."
        return None
    if not all(token_satisfied(hay_words, token) for token in required):
        return None
    direct = all(word_matches(hay_words, token) for token in required)
    if direct:
        return 0.88, f"Matched your interest “{interest}”."
    return 0.76, f"“{interest}” matches this offer beyond the exact spelling."


def nearest_store(stores: list[StoreLocation], chain: str) -> str:
    best: StoreLocation | None = None
    for store in stores:
        if same_chain(store.chain, chain) or same_chain(store.name, chain):
            if best is None or (store.distance_m or 1e18) < (best.distance_m or 1e18):
                best = store
    if best is None:
        return chain
    return best.name


def keyword_matches(
    offers: list[Offer],
    interests: list[str],
    stores: list[StoreLocation],
    min_confidence: float,
) -> list[MatchDraft]:
    drafts: list[MatchDraft] = []
    seen: set[str] = set()
    for offer in offers:
        words = offer_words(offer)
        for interest in interests:
            scored = score_interest(words, interest)
            if scored is None:
                continue
            confidence, reason = scored
            if confidence < min_confidence:
                continue
            store_name = nearest_store(stores, offer.chain) if offer.chain else offer.store_name
            draft = MatchDraft(
                fingerprint=fingerprint(
                    source=offer.source,
                    external_id=offer.external_id,
                    interest=interest,
                    price=offer.price,
                    valid_to=offer.valid_to,
                ),
                interest=interest,
                product=offer.product or "Offer",
                description=offer.description or "",
                price=offer.price,
                original_price=offer.old_price,
                discount=discount_label(offer.price, offer.old_price),
                store_name=store_name or offer.chain,
                chain=offer.chain,
                valid_from=offer.valid_from,
                valid_to=offer.valid_to,
                confidence=confidence,
                reason=reason,
                image_url=offer.image_url,
                link_url=offer.link_url,
                source=offer.source,
                external_id=offer.external_id,
            )
            if draft.fingerprint in seen:
                continue
            seen.add(draft.fingerprint)
            drafts.append(draft)
    return drafts
