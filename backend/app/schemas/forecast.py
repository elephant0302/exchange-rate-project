from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.exchange import ForecastPointOut


class ForecastOut(BaseModel):
    available: bool
    unavailable_reason: str | None = None
    pair: str
    model_name: str | None = None
    horizon_days: int = 30
    confidence_level: float | None = None
    trained_from: date | None = None
    trained_to: date | None = None
    mae: float | None = None
    rmse: float | None = None
    created_at: datetime | None = None
    disclaimer: str = "통계적 추정치이며 실제 환율과 다를 수 있습니다."
    points: list[ForecastPointOut] = []
