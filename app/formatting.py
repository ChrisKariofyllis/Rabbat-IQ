"""Display formatting for prices, dates, and distances."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return ensure_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_euro(value: float | None) -> str:
    if value is None:
        return ""
    whole, frac = f"{value:.2f}".split(".")
    return f"{whole},{frac} €"


def discount_label(price: float | None, old_price: float | None) -> str:
    if price is None or old_price is None or old_price <= 0 or price >= old_price:
        return ""
    percent = round((1 - price / old_price) * 100)
    if percent <= 0:
        return ""
    return f"−{percent}%"


def format_date(value) -> str:
    parsed = value if isinstance(value, datetime) else parse_dt(value)
    moment = ensure_utc(parsed)
    if moment is None:
        return ""
    local = moment.astimezone(BERLIN)
    return local.strftime("%d %b").lstrip("0")


def validity_label(start, end) -> str:
    left = format_date(start)
    right = format_date(end)
    if left and right:
        return f"{left} – {right}"
    return right or left


def format_distance(meters: float | None) -> str:
    if meters is None:
        return ""
    if meters < 950:
        return f"{round(meters)} m"
    return f"{meters / 1000:.1f} km"


def format_when(value) -> str:
    moment = ensure_utc(value if isinstance(value, datetime) else parse_dt(value))
    if moment is None:
        return ""
    local = moment.astimezone(BERLIN)
    return local.strftime("%d %b %H:%M").lstrip("0")
