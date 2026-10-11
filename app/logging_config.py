"""Logging setup. API keys are never written by the formatters here."""

import logging


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    resolved = getattr(logging, level.upper(), logging.INFO)
    if not root.handlers:
        logging.basicConfig(
            level=resolved,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    root.setLevel(resolved)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)
