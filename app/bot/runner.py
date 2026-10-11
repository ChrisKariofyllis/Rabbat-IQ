"""Start and stop the Telegram polling bot with the web process."""

import logging

from app.config import get_env
from app.services.repository import get_settings

log = logging.getLogger(__name__)


class BotRunner:
    def __init__(self) -> None:
        self.application = None
        self.token = ""

    async def sync(self) -> None:
        if get_env().disable_bot:
            return
        settings = get_settings()
        token = (settings.telegram_bot_token or "").strip()
        if token == self.token and self.application is not None:
            return
        await self.stop()
        if not token:
            return
        try:
            await self._start(token)
        except Exception:
            log.exception("telegram bot failed to start")
            self.token = ""

    async def stop(self) -> None:
        application = self.application
        self.application = None
        self.token = ""
        if application is None:
            return
        try:
            if application.updater is not None:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()
        except Exception:
            log.exception("telegram bot shutdown failed")

    async def _start(self, token: str) -> None:
        from telegram.ext import Application

        from app.bot.handlers import register

        application = Application.builder().token(token).build()
        register(application)
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        self.application = application
        self.token = token
        log.info("telegram bot polling started")


bot_runner = BotRunner()
