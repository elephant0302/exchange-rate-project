from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.database import SessionLocal
from app.services.ingest import cleanup_news, generate_forecasts, ingest_exchange_rates, ingest_news

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_job(name: str, func) -> None:
    db = SessionLocal()
    try:
        func(db)
    except Exception:
        logger.exception("Scheduled job %s failed", name)
    finally:
        db.close()


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: _run_job("exchange", ingest_exchange_rates),
        IntervalTrigger(minutes=settings.exchange_sync_minutes),
        id="exchange_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_job("news", ingest_news),
        IntervalTrigger(minutes=settings.news_sync_minutes),
        id="news_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_job("forecast", generate_forecasts),
        IntervalTrigger(minutes=settings.forecast_sync_minutes),
        id="forecast_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_job("news_cleanup", cleanup_news),
        IntervalTrigger(hours=settings.news_cleanup_hours),
        id="news_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Scheduler started (exchange=%sm news=%sm forecast=%sm cleanup=%sh). "
        "Running multiple app instances will duplicate these jobs.",
        settings.exchange_sync_minutes,
        settings.news_sync_minutes,
        settings.forecast_sync_minutes,
        settings.news_cleanup_hours,
    )
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
