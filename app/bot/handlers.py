"""Telegram commands. Only the configured chat id may use them.

Until a chat id is saved, /start replies with the id of the chat that sent it
so you can paste it into settings. Other commands stay quiet.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.formatting import format_distance, format_when
from app.services import repository
from app.services.scan import scan_status, try_start_scan

log = logging.getLogger(__name__)


def register(application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chatid", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("interests", interests))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("stores", stores))
    application.add_handler(CommandHandler("scan_now", scan_now))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    settings = repository.get_settings()
    expected = (settings.telegram_chat_id or "").strip()
    if not expected:
        await update.message.reply_text(
            f"This chat id is {chat.id}.\n"
            "Paste it into Markthunter settings next to your bot token, then send /start again."
        )
        return
    if str(chat.id) != expected:
        return
    await update.message.reply_text("Markthunter is listening.\n" + _help_text())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.message.reply_text(_help_text())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    settings = repository.get_settings()
    current = scan_status()
    last = current["last"]
    lines = [
        f"Place: {settings.place_name or 'not scanned yet'} {settings.postal_code}".strip(),
        f"Radius: {settings.radius_km:g} km",
        f"Interests: {len(repository.list_interests())}",
        f"Matches saved: {repository.count_matches()}",
    ]
    if current["running"]:
        lines.append("A scan is running.")
    elif last:
        lines.append(f"Last scan ({last['trigger']}): {last['message'] or last['status']}")
        if last["finished_at"]:
            lines.append(f"Finished {format_when(last['finished_at'])}")
    else:
        lines.append("No scan yet.")
    if current["next_scan_at"] and not current["running"]:
        lines.append(f"Next automatic scan {format_when(current['next_scan_at'])}")
    await update.message.reply_text("\n".join(lines))


async def interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = repository.list_interests()
    if not rows:
        await update.message.reply_text("No interests yet. Add one with /add Greek yogurt")
        return
    lines = [row.text for row in rows]
    await update.message.reply_text("Interests:\n" + "\n".join(f"• {line}" for line in lines))


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    text = " ".join(context.args or []).strip()
    result = repository.add_interest(text)
    messages = {
        "added": f"Added “{text}”.",
        "duplicate": "That interest is already on the list.",
        "empty": "Usage: /add Greek yogurt",
        "long": "Keep an interest under 80 characters.",
        "limit": "The list is full (30 interests).",
    }
    await update.message.reply_text(messages.get(result, "Could not add that interest."))


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await update.message.reply_text("Usage: /remove Greek yogurt")
        return
    if repository.delete_interest_text(text):
        await update.message.reply_text(f"Removed “{text}”.")
        return
    await update.message.reply_text("That interest is not on the list.")


async def stores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = repository.list_stores()[:8]
    if not rows:
        await update.message.reply_text("No stores yet. Run /scan_now after setting a postal code.")
        return
    lines = []
    for row in rows:
        distance = format_distance(row.distance_m)
        suffix = f" · {distance}" if distance else ""
        lines.append(f"• {row.name}{suffix}")
    await update.message.reply_text("Nearest stores:\n" + "\n".join(lines))


async def scan_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    settings = repository.get_settings()
    if not (settings.postal_code or "").strip():
        await update.message.reply_text("Set a postal code in the web UI first.")
        return
    if not repository.list_interests():
        await update.message.reply_text("Add an interest first, for example /add beer")
        return
    outcome = try_start_scan("telegram")
    if outcome == "busy":
        await update.message.reply_text("A scan is already running.")
        return
    await update.message.reply_text("Scan started. I'll message you here if something matches.")


def _help_text() -> str:
    return (
        "/status — last scan and next run\n"
        "/interests — list interests\n"
        "/add beer — add an interest\n"
        "/remove beer — remove an interest\n"
        "/stores — nearest stores from the last scan\n"
        "/scan_now — run a scan"
    )


async def _guard(update: Update) -> bool:
    message = update.message
    chat = update.effective_chat
    if message is None or chat is None:
        return False
    settings = repository.get_settings()
    expected = (settings.telegram_chat_id or "").strip()
    if not expected or str(chat.id) != expected:
        return False
    return True
