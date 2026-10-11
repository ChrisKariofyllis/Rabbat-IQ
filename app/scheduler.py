"""Run a scan on the interval saved in settings.

The clock ticks once a minute and starts a scan only when the configured
interval has elapsed. Changing the interval in the UI takes effect without a
restart.
"""

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.formatting import ensure_utc, utcnow
from app.services.repository import fail_stale_scan, get_settings, latest_scan, list_interests
from app.services.scan import try_start_scan

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    _scheduler.add_job(scheduled_tick, "interval", minutes=1, id="markthunter-tick", max_instances=1, coalesce=True)
    _scheduler.start()
    log.info("scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None


async def scheduled_tick() -> None:
    settings = get_settings()
    if not (settings.postal_code or "").strip():
        return
    if not list_interests():
        return
    fail_stale_scan()
    last = latest_scan()
    interval = max(15, int(settings.scan_interval_minutes or 30))
    if last is not None and last.status == "running":
        return
    if last is not None and last.started_at is not None:
        started = ensure_utc(last.started_at)
        if started is not None and utcnow() - started < timedelta(minutes=interval):
            return
    outcome = try_start_scan("schedule")
    if outcome == "started":
        log.info("scheduled scan started")
