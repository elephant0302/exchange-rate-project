from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.exchange import router as exchange_router
from app.api.forecasts import router as forecast_router
from app.api.health import router as health_router
from app.api.indicators import router as indicator_router
from app.api.news import router as news_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import CollectionStatus, Event, Forecast, Indicator, Observation  # noqa: F401
from app.scheduler import start_scheduler, stop_scheduler
from app.services.catalog import seed_indicators
from app.services.ingest import refresh_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _run_startup_refresh() -> None:
    db = SessionLocal()
    try:
        seed_indicators(db)
        result = refresh_all(db)
        logger.info("Startup refresh finished: %s", {k: v.get("added", v.get("generated")) for k, v in result.items()})
    except Exception:
        logger.exception("Startup refresh failed; serving stored data if available")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_indicators(db)
    finally:
        db.close()
    if settings.auto_ingest_on_startup:
        _run_startup_refresh()
    if settings.scheduler_enabled:
        start_scheduler(settings)
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(indicator_router, prefix="/api")
    application.include_router(exchange_router, prefix="/api")
    application.include_router(news_router, prefix="/api")
    application.include_router(forecast_router, prefix="/api")
    application.include_router(admin_router, prefix="/api")
    return application


app = create_app()
