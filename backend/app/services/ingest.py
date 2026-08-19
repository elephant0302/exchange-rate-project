from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Event, Forecast, Observation
from app.providers.base import ForecastResult, NewsArticle, RateObservation
from app.providers.exchange import build_exchange_provider
from app.providers.exchange.mock import MockExchangeProvider
from app.providers.forecast import build_forecast_provider
from app.providers.news import build_news_provider
from app.providers.news.classifier import infer_pair
from app.providers.news.historical import HistoricalNewsProvider, month_windows
from app.providers.news.mock import MockNewsProvider
from app.services.catalog import (
    PAIR_CNY_KRW,
    PAIR_EUR_KRW,
    PAIR_JPY_KRW,
    SUPPORTED_PAIRS,
    get_indicator,
    seed_indicators,
)
from app.services.query import pair_text_clauses
from app.services.normalize import normalize_url, utcnow
from app.services.status import upsert_status

logger = logging.getLogger(__name__)


def _existing_dates(db: Session, indicator_id: int) -> set[date]:
    rows = db.scalars(
        select(Observation.observed_at).where(Observation.indicator_id == indicator_id)
    ).all()
    return set(rows)


def _save_observations(db: Session, indicator_id: int, points: list[RateObservation]) -> int:
    existing = _existing_dates(db, indicator_id)
    added = 0
    for point in points:
        if point.observed_at in existing:
            continue
        db.add(
            Observation(
                indicator_id=indicator_id,
                observed_at=point.observed_at,
                value=point.value,
                source=point.source,
                is_mock=point.is_mock,
                collected_at=utcnow(),
            )
        )
        existing.add(point.observed_at)
        added += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("Skipped duplicate observations for indicator %s", indicator_id)
    return added


def ingest_exchange_rates(
    db: Session,
    settings: Settings | None = None,
    pairs: tuple[str, ...] = SUPPORTED_PAIRS,
) -> dict:
    settings = settings or get_settings()
    seed_indicators(db)
    provider = build_exchange_provider(settings)
    start = date.fromisoformat(settings.history_start_date)
    end = date.today()
    warnings: list[str] = []
    added_total = 0
    used_mock = provider.is_mock

    try:
        for pair in pairs:
            indicator = get_indicator(db, pair)
            if indicator is None:
                continue
            points = provider.fetch_history(pair, start, end)
            added_total += _save_observations(db, indicator.id, points)
        source = "Mock 일별 시계열 (실제 환율 아님)" if used_mock else "Frankfurter (ECB 일별 환율)"
        upsert_status(
            db,
            "exchange",
            status="mock" if used_mock else "success",
            source=source,
            message=f"{added_total}개 관측치 추가",
            is_mock=used_mock,
            success=True,
        )
        return {"added": added_total, "is_mock": used_mock, "source": source, "warnings": warnings}
    except Exception as exc:
        logger.exception("Exchange ingest failed: %s", exc)
        warnings.append(f"환율 수집 실패: {exc.__class__.__name__}")
        has_data = db.scalar(select(Observation.id).limit(1)) is not None
        if settings.allow_mock_fallback and not has_data:
            mock = MockExchangeProvider()
            for pair in pairs:
                indicator = get_indicator(db, pair)
                if indicator is None:
                    continue
                added_total += _save_observations(
                    db, indicator.id, mock.fetch_history(pair, end - timedelta(days=400), end)
                )
            upsert_status(
                db,
                "exchange",
                status="mock",
                source="Mock 일별 시계열 (실제 환율 아님)",
                message=f"외부 수집 실패 후 Mock 사용: {exc}",
                is_mock=True,
                success=True,
            )
            return {
                "added": added_total,
                "is_mock": True,
                "source": "Mock 일별 시계열 (실제 환율 아님)",
                "warnings": warnings,
            }
        upsert_status(
            db,
            "exchange",
            status="failed",
            source="Frankfurter (ECB 일별 환율)",
            message=str(exc),
            is_mock=False,
            success=False,
        )
        return {
            "added": 0,
            "is_mock": False,
            "source": "Frankfurter (ECB 일별 환율)",
            "warnings": warnings,
        }


def _save_news(db: Session, articles: list[NewsArticle]) -> int:
    added = 0
    existing_urls = set(db.scalars(select(Event.normalized_url)).all())
    for article in articles:
        url_key = normalize_url(article.url)
        if not url_key or url_key in existing_urls:
            continue
        indicator = get_indicator(db, article.pair) if article.pair else None
        db.add(
            Event(
                indicator_id=indicator.id if indicator else None,
                title=article.title[:512],
                url=article.url[:1024],
                normalized_url=url_key[:1024],
                source=article.source[:128],
                published_at=article.published_at,
                collected_at=utcnow(),
                direction=article.direction,
                importance=article.importance,
                summary=article.summary,
                keywords=",".join(article.keywords),
                is_mock=article.is_mock,
            )
        )
        existing_urls.add(url_key)
        added += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("Skipped duplicate news rows")
    return added


def _month_has_enough_news(db: Session, start: date, end: date, minimum: int) -> bool:
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    count = db.scalar(
        select(func.count(Event.id)).where(
            Event.published_at >= start_dt,
            Event.published_at < end_dt,
        )
    )
    return int(count or 0) >= minimum


def _month_has_enough_pair_news(
    db: Session, start: date, end: date, minimum: int, pair: str
) -> bool:
    indicator = get_indicator(db, pair)
    if indicator is None:
        return False
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    count = db.scalar(
        select(func.count(Event.id)).where(
            Event.published_at >= start_dt,
            Event.published_at < end_dt,
            or_(Event.indicator_id == indicator.id, *pair_text_clauses(pair)),
        )
    )
    return int(count or 0) >= minimum


def _retag_news_pairs(db: Session) -> int:
    updated = 0
    for row in db.scalars(select(Event)).all():
        blob = f"{row.title} {row.summary or ''} {row.keywords or ''}"
        inferred = infer_pair(blob, fallback=None)
        if not inferred:
            continue
        indicator = get_indicator(db, inferred)
        if indicator is None or row.indicator_id == indicator.id:
            continue
        row.indicator_id = indicator.id
        updated += 1
    if updated:
        db.commit()
    return updated


def ingest_news(db: Session, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    seed_indicators(db)
    provider = build_news_provider(settings)
    try:
        end = date.today()
        start = end - timedelta(days=max(settings.news_history_months, 1) * 31)
        articles = list(provider.fetch_news(start=None, end=None))
        if not provider.is_mock:
            historical = HistoricalNewsProvider()
            missing = [
                window
                for window in month_windows(start, end)
                if not _month_has_enough_news(
                    db, window[0], window[1], settings.news_history_min_per_month
                )
            ]
            for window_start, window_end in list(reversed(missing))[: settings.news_history_batch_months]:
                articles.extend(historical.fetch_range(None, window_start, window_end))
            for pair in (PAIR_CNY_KRW, PAIR_EUR_KRW, PAIR_JPY_KRW):
                pair_missing = [
                    window
                    for window in month_windows(start, end)
                    if not _month_has_enough_pair_news(
                        db, window[0], window[1], settings.news_history_min_per_month, pair
                    )
                ]
                for window_start, window_end in list(reversed(pair_missing))[
                    : settings.news_history_batch_months
                ]:
                    articles.extend(historical.fetch_range(pair, window_start, window_end))
        else:
            articles = list(provider.fetch_news(start=start, end=end))
        added = _save_news(db, articles)
        retagged = _retag_news_pairs(db)
        source = (
            "Mock 샘플 헤드라인 (실제 기사 아님)"
            if provider.is_mock
            else "RSS + 과거 뉴스 (Google News 기간검색, GDELT)"
        )
        upsert_status(
            db,
            "news",
            status="mock" if provider.is_mock else "success",
            source=source,
            message=f"{added}개 기사 추가, {retagged}개 통화 재분류",
            is_mock=provider.is_mock,
            success=True,
        )
        return {"added": added, "is_mock": provider.is_mock, "source": source, "warnings": []}
    except Exception as exc:
        logger.exception("News ingest failed: %s", exc)
        has_data = db.scalar(select(Event.id).limit(1)) is not None
        if settings.allow_mock_fallback and not has_data:
            added = _save_news(db, MockNewsProvider().fetch_news())
            upsert_status(
                db,
                "news",
                status="mock",
                source="Mock 샘플 헤드라인 (실제 기사 아님)",
                message=f"외부 수집 실패 후 Mock 사용: {exc}",
                is_mock=True,
                success=True,
            )
            return {
                "added": added,
                "is_mock": True,
                "source": "Mock 샘플 헤드라인 (실제 기사 아님)",
                "warnings": [f"뉴스 수집 실패: {exc.__class__.__name__}"],
            }
        upsert_status(
            db,
            "news",
            status="failed",
            source="RSS",
            message=str(exc),
            is_mock=False,
            success=False,
        )
        return {
            "added": 0,
            "is_mock": False,
            "source": "RSS",
            "warnings": [f"뉴스 수집 실패: {exc.__class__.__name__}"],
        }


def persist_forecast(db: Session, indicator_id: int, result: ForecastResult, is_mock: bool) -> int:
    if not result.available:
        return 0
    created_at = utcnow()
    for point in result.points:
        db.add(
            Forecast(
                indicator_id=indicator_id,
                target_at=point.target_at,
                predicted_value=point.predicted_value,
                lower_bound=point.lower_bound,
                upper_bound=point.upper_bound,
                confidence_level=result.confidence_level,
                model_name=result.model_name or "unknown",
                trained_from=result.trained_from,
                trained_to=result.trained_to,
                mae=result.mae,
                rmse=result.rmse,
                horizon_days=len(result.points),
                is_mock=is_mock,
                created_at=created_at,
            )
        )
    db.commit()
    return len(result.points)


def generate_forecasts(
    db: Session,
    pairs: tuple[str, ...] = SUPPORTED_PAIRS,
    horizon: int = 30,
) -> dict:
    seed_indicators(db)
    provider = build_forecast_provider()
    generated = 0
    reasons: list[str] = []
    for pair in pairs:
        indicator = get_indicator(db, pair)
        if indicator is None:
            continue
        rows = db.execute(
            select(Observation.observed_at, Observation.value, Observation.is_mock)
            .where(Observation.indicator_id == indicator.id)
            .order_by(Observation.observed_at.asc())
        ).all()
        dates = [row[0] for row in rows]
        values = [row[1] for row in rows]
        is_mock = any(row[2] for row in rows)
        result = provider.generate(pair, dates, values, horizon=horizon)
        if not result.available:
            reasons.append(f"{pair}: {result.unavailable_reason}")
            continue
        generated += persist_forecast(db, indicator.id, result, is_mock=is_mock)
    upsert_status(
        db,
        "forecast",
        status="success" if generated else "failed",
        source="통계 모델 (Naive / 최근 Drift / LocalMean / ARIMA)",
        message=f"{generated}개 예측점 저장. " + "; ".join(reasons),
        is_mock=False,
        success=generated > 0,
    )
    return {"generated": generated, "warnings": reasons}


def cleanup_news(db: Session, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    cutoff = utcnow() - timedelta(days=settings.news_retention_days)
    result = db.execute(delete(Event).where(Event.published_at < cutoff))
    db.commit()
    deleted = result.rowcount or 0
    upsert_status(
        db,
        "news_cleanup",
        status="success",
        source="local",
        message=f"{deleted}개 오래된 뉴스 삭제",
        is_mock=False,
        success=True,
    )
    return deleted


def refresh_all(db: Session, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    exchange = ingest_exchange_rates(db, settings)
    news = ingest_news(db, settings)
    forecast = generate_forecasts(db)
    return {"exchange": exchange, "news": news, "forecast": forecast}
