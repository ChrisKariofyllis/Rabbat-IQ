"""Send match alerts through the Telegram Bot API.

Commands are handled separately by the polling bot. Sending only needs the
token and chat id, so a scan can notify even when polling is turned off.
"""

import asyncio
import logging

import httpx

from app.formatting import format_euro, validity_label
from app.services import repository

log = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


def esc(value: str | None) -> str:
    text = value or ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_message(match) -> str:
    lines = [f"<b>{esc(match.product)}</b>"]
    price = format_euro(match.price)
    if price:
        extras = ""
        old = format_euro(match.original_price)
        if old and match.original_price and match.price is not None and match.original_price > match.price:
            extras += f"  <s>{old}</s>"
        if match.discount:
            extras += f"  {esc(match.discount)}"
        lines.append(price + extras)
    where = match.store_name or match.chain
    if where:
        lines.append(esc(where))
    when = validity_label(match.valid_from, match.valid_to)
    if when:
        lines.append(f"Valid {esc(when)}")
    if match.interest:
        lines.append(f"Interest: {esc(match.interest)}")
    if match.reason:
        lines.append(esc(match.reason))
    if match.link_url:
        lines.append(f'<a href="{esc(match.link_url)}">Open offer</a>')
    text = "\n".join(lines)
    return text[:1000]


async def send_message(token: str, chat_id: str, text: str) -> None:
    await _post(token, "sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


async def send_match(token: str, chat_id: str, match) -> None:
    caption = render_message(match)
    image = (match.image_url or "").strip()
    if image:
        try:
            await _post(
                token,
                "sendPhoto",
                {"chat_id": chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"},
            )
            return
        except TelegramError:
            log.info("telegram photo failed, sending text only")
    await send_message(token, chat_id, caption)


async def notify_pending(limit: int = 15) -> int:
    settings = repository.get_settings()
    token = (settings.telegram_bot_token or "").strip()
    chat_id = (settings.telegram_chat_id or "").strip()
    pending = repository.list_pending_matches(limit=limit)
    if not pending or not token or not chat_id:
        return 0
    sent = 0
    for match in pending:
        try:
            await send_match(token, chat_id, match)
            repository.mark_notified(match.id)
            sent += 1
        except TelegramError as exc:
            repository.mark_notify_failed(match.id, str(exc))
            log.warning("telegram notify failed for match %s", match.id)
        await asyncio.sleep(0.35)
    return sent


async def _post(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise TelegramError("Could not reach Telegram.") from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise TelegramError(f"Telegram returned HTTP {response.status_code}.") from exc
    if response.status_code >= 400 or not body.get("ok"):
        description = str(body.get("description") or f"HTTP {response.status_code}")
        if token:
            description = description.replace(token, "[token]")
        raise TelegramError(description[:300])
    return body
