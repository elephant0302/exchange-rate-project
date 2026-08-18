from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CollectionStatus, Event, Forecast, Indicator, Observation
from app.providers.news.classifier import DIRECTION_LABELS, IMPORTANCE_LABELS, PAIR_HINTS
from app.schemas.common import ResponseMeta
from app.schemas.exchange import (
    EventMarker,
    ForecastPointOut,
    HistoryOut,
    LatestForecastSummary,
    LatestRateOut,
    RatePoint,
)
from app.schemas.forecast import ForecastOut
from app.schemas.news import NewsItemOut
from app.services.catalog import parse_extra, require_pair
from app.services.normalize import change_amount, change_pct, period_start, realized_volatility


def _indicator(db: Session, pair: str) -> Indicator:
    code = require_pair(pair)
    indicator = db.scalar(select(Indicator).where(Indicator.code == code))
    if indicator is None:
        raise ValueError(f"Unknown indicator: {code}")
    return indicator


def pair_text_clauses(pair: str) -> list:
    clauses = []
    for hint in PAIR_HINTS.get(pair, ()):
        pattern = f"%{hint}%"
        clauses.append(Event.title.ilike(pattern))
        clauses.append(Event.keywords.ilike(pattern))
        clauses.append(Event.summary.ilike(pattern))
    return clauses


def news_event_filter(indicator: Indicator, pair: str):
    return or_(
        Event.indicator_id == indicator.id,
        Event.indicator_id.is_(None),
        *pair_text_clauses(pair),
    )


def select_news_across_months(rows: list[Event], limit: int) -> list[Event]:
    """Keep coverage across the selected period instead of only the newest rows."""
    if limit <= 0 or len(rows) <= limit:
        return rows
    buckets: dict[str, list[Event]] = {}
    for row in rows:
        buckets.setdefault(row.published_at.strftime("%Y-%m"), []).append(row)
    per_month = max(1, limit // len(buckets))
    chosen: list[Event] = []
    leftovers: list[Event] = []
    for key in sorted(buckets):
        month_rows = buckets[key]
        chosen.extend(month_rows[:per_month])
        leftovers.extend(month_rows[per_month:])
    leftover_slots = limit - len(chosen)
    if leftover_slots > 0:
        leftovers.sort(key=lambda row: row.published_at, reverse=True)
        chosen.extend(leftovers[:leftover_slots])
    chosen.sort(key=lambda row: row.published_at, reverse=True)
    return chosen[:limit]


def _observations(db: Session, indicator_id: int, start: date | None = None) -> list[Observation]:
    stmt = select(Observation).where(Observation.indicator_id == indicator_id)
    if start is not None:
        stmt = stmt.where(Observation.observed_at >= start)
    return list(db.scalars(stmt.order_by(Observation.observed_at.asc())).all())


def _latest_forecast_batch(db: Session, indicator_id: int) -> list[Forecast]:
    latest_created = db.scalar(
        select(Forecast.created_at)
        .where(Forecast.indicator_id == indicator_id)
        .order_by(Forecast.created_at.desc())
        .limit(1)
    )
    if latest_created is None:
        return []
    return list(
        db.scalars(
            select(Forecast)
            .where(
                Forecast.indicator_id == indicator_id,
                Forecast.created_at == latest_created,
            )
            .order_by(Forecast.target_at.asc())
        ).all()
    )


def _collection_meta(db: Session, job_name: str, indicator: Indicator, extra_warnings: list[str]) -> ResponseMeta:
    status = db.get(CollectionStatus, job_name)
    latest_obs = db.scalar(
        select(Observation)
        .where(Observation.indicator_id == indicator.id)
        .order_by(Observation.observed_at.desc())
    )
    is_mock = bool(status.is_mock) if status else bool(latest_obs and latest_obs.is_mock)
    warnings = list(extra_warnings)
    if status and status.status == "failed":
        warnings.append(f"데이터 수집 실패: {status.message}")
    if is_mock:
        warnings.append("현재 표시 중인 환율은 Mock 데이터이며 실제 시장 환율이 아닙니다.")
    source = (
        (status.source if status and status.source else None)
        or (latest_obs.source if latest_obs else indicator.source)
    )
    last_updated = None
    if latest_obs is not None:
        last_updated = latest_obs.collected_at
    if status and status.last_success_at:
        last_updated = status.last_success_at
    return ResponseMeta(
        source=source or indicator.source,
        last_updated_at=last_updated,
        unit=indicator.unit,
        unit_label=indicator.unit_label,
        frequency=indicator.frequency,
        is_mock=is_mock,
        warnings=warnings,
        pair=indicator.code,
    )


def latest_rate(db: Session, pair: str, period: str = "1Y") -> tuple[LatestRateOut, ResponseMeta]:
    indicator = _indicator(db, pair)
    start = period_start(period)
    rows = _observations(db, indicator.id, start)
    all_rows = _observations(db, indicator.id)
    latest = all_rows[-1] if all_rows else None
    previous = all_rows[-2] if len(all_rows) >= 2 else None
    values = [row.value for row in rows]
    forecasts = _latest_forecast_batch(db, indicator.id)
    day_30 = next((item for item in forecasts if item.horizon_days >= 30), None)
    if forecasts:
        day_30 = forecasts[min(len(forecasts) - 1, 29)]
    forecast_summary = LatestForecastSummary(
        available=bool(forecasts),
        predicted_value=day_30.predicted_value if day_30 else None,
        lower_bound=day_30.lower_bound if day_30 else None,
        upper_bound=day_30.upper_bound if day_30 else None,
        model_name=day_30.model_name if day_30 else None,
        horizon_days=30 if day_30 else None,
    )
    data = LatestRateOut(
        pair=indicator.code,
        observed_at=latest.observed_at if latest else None,
        value=latest.value if latest else None,
        previous_value=previous.value if previous else None,
        change_value=change_amount(latest.value, previous.value) if latest and previous else None,
        change_pct=change_pct(latest.value, previous.value) if latest and previous else None,
        period_high=max(values) if values else None,
        period_low=min(values) if values else None,
        volatility=realized_volatility(values),
        forecast_30d=forecast_summary,
    )
    extra = []
    if latest is None:
        extra.append("저장된 환율 데이터가 없습니다. 관리자 새로고침을 실행하세요.")
    return data, _collection_meta(db, "exchange", indicator, extra)


def history(db: Session, pair: str, period: str) -> tuple[HistoryOut, ResponseMeta]:
    indicator = _indicator(db, pair)
    start = period_start(period)
    rows = _observations(db, indicator.id, start)
    event_stmt = select(Event).where(news_event_filter(indicator, indicator.code))
    if start is not None:
        event_stmt = event_stmt.where(Event.published_at >= start)
    events = list(db.scalars(event_stmt.order_by(Event.published_at.asc())).all())
    data = HistoryOut(
        pair=indicator.code,
        points=[RatePoint(observed_at=row.observed_at, value=row.value) for row in rows],
        events=[
            EventMarker(
                id=event.id,
                published_at=event.published_at,
                title=event.title,
                importance=event.importance,
                direction=event.direction,
            )
            for event in events
        ],
    )
    extra = []
    if not rows:
        extra.append("선택한 기간에 환율 데이터가 없습니다.")
    return data, _collection_meta(db, "exchange", indicator, extra)


def news_list(
    db: Session,
    pair: str,
    limit: int = 200,
    period: str | None = None,
) -> tuple[list[NewsItemOut], ResponseMeta]:
    indicator = _indicator(db, pair)
    stmt = select(Event).where(news_event_filter(indicator, indicator.code))
    if period:
        start = period_start(period)
        if start is not None:
            stmt = stmt.where(
                Event.published_at
                >= datetime.combine(start, time.min, tzinfo=timezone.utc)
            )
    rows = list(db.scalars(stmt.order_by(Event.published_at.desc())).all())
    used_general_fallback = False
    if not rows:
        fallback = select(Event)
        if period:
            start = period_start(period)
            if start is not None:
                fallback = fallback.where(
                    Event.published_at
                    >= datetime.combine(start, time.min, tzinfo=timezone.utc)
                )
        rows = list(db.scalars(fallback.order_by(Event.published_at.desc())).all())
        used_general_fallback = bool(rows)
    truncated = len(rows) > limit
    rows = select_news_across_months(rows, limit)
    items = [
        NewsItemOut(
            id=row.id,
            title=row.title,
            url=row.url,
            source=row.source,
            published_at=row.published_at,
            collected_at=row.collected_at,
            pair=indicator.code if row.indicator_id == indicator.id else None,
            direction=row.direction,
            direction_label=DIRECTION_LABELS.get(row.direction, "중립 또는 불명확"),
            importance=row.importance,
            importance_label=IMPORTANCE_LABELS.get(row.importance, "보통"),
            summary=row.summary,
            keywords=[item for item in row.keywords.split(",") if item],
            is_mock=row.is_mock,
        )
        for row in rows
    ]
    status = db.get(CollectionStatus, "news")
    warnings = []
    is_mock = bool(status.is_mock) if status else any(item.is_mock for item in items)
    if status and status.status == "failed":
        warnings.append(f"뉴스 수집 실패: {status.message}")
    if is_mock:
        warnings.append("표시 중인 일부 또는 전체 뉴스는 Mock 샘플이며 실제 기사가 아닙니다.")
    if used_general_fallback:
        warnings.append(
            f"{indicator.name} 전용 기사가 부족해 같은 기간의 원화 환율 관련 뉴스를 함께 표시합니다."
        )
    if truncated:
        warnings.append("기사가 많아 월별로 나눠 표시합니다. 기간을 줄이면 해당 구간의 기사를 더 볼 수 있습니다.")
    if not items:
        warnings.append("관련 뉴스가 없습니다. 외부 RSS가 차단되었거나 아직 수집되지 않았습니다.")
    extra = parse_extra(indicator.extra)
    _ = extra
    meta = ResponseMeta(
        source=(status.source if status and status.source else "RSS"),
        last_updated_at=status.last_success_at if status else None,
        unit=indicator.unit,
        unit_label=indicator.unit_label,
        is_mock=is_mock,
        warnings=warnings,
        pair=indicator.code,
    )
    return items, meta


def forecasts(db: Session, pair: str, horizon: int = 30) -> tuple[ForecastOut, ResponseMeta]:
    indicator = _indicator(db, pair)
    rows = _latest_forecast_batch(db, indicator.id)
    if horizon in (7, 30) and rows:
        rows = rows[:horizon]
    if not rows:
        obs_count = len(_observations(db, indicator.id))
        reason = (
            f"예측에 필요한 일별 데이터가 부족합니다. 최소 90영업일이 필요하지만 현재 {obs_count}일입니다."
            if obs_count < 90
            else "저장된 예측이 없습니다. 관리자 예측 생성을 실행하세요."
        )
        data = ForecastOut(available=False, unavailable_reason=reason, pair=indicator.code)
        return data, _collection_meta(db, "forecast", indicator, [reason])

    first = rows[0]
    data = ForecastOut(
        available=True,
        pair=indicator.code,
        model_name=first.model_name,
        horizon_days=horizon,
        confidence_level=first.confidence_level,
        trained_from=first.trained_from,
        trained_to=first.trained_to,
        mae=first.mae,
        rmse=first.rmse,
        created_at=first.created_at,
        points=[
            ForecastPointOut(
                target_at=row.target_at,
                predicted_value=row.predicted_value,
                lower_bound=row.lower_bound,
                upper_bound=row.upper_bound,
            )
            for row in rows
        ],
    )
    extra = ["통계적 추정치이며 실제 환율과 다를 수 있습니다."]
    if first.is_mock:
        extra.append("학습 데이터가 Mock이므로 예측 결과도 실제 시장과 무관합니다.")
    return data, _collection_meta(db, "forecast", indicator, extra)
