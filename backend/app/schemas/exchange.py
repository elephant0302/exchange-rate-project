from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class RatePoint(BaseModel):
    observed_at: date
    value: float


class EventMarker(BaseModel):
    id: int
    published_at: datetime
    title: str
    importance: str
    direction: str


class ForecastPointOut(BaseModel):
    target_at: date
    predicted_value: float
    lower_bound: float
    upper_bound: float


class LatestForecastSummary(BaseModel):
    available: bool
    predicted_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    model_name: str | None = None
    horizon_days: int | None = None


class LatestRateOut(BaseModel):
    pair: str
    observed_at: date | None
    value: float | None
    previous_value: float | None
    change_value: float | None
    change_pct: float | None
    period_high: float | None
    period_low: float | None
    volatility: float | None
    forecast_30d: LatestForecastSummary


class HistoryOut(BaseModel):
    pair: str
    points: list[RatePoint]
    events: list[EventMarker]
