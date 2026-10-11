"""Stable ids so the same offer is not notified twice."""

import hashlib

from app.formatting import ensure_utc
from app.textutil import normalize


def fingerprint(
    *,
    source: str,
    external_id: str,
    interest: str,
    price: float | None,
    valid_to,
) -> str:
    moment = ensure_utc(valid_to)
    raw = "|".join(
        [
            source or "",
            external_id or "",
            normalize(interest),
            "" if price is None else f"{price:.2f}",
            "" if moment is None else moment.date().isoformat(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
