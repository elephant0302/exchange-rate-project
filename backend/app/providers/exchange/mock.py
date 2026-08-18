from __future__ import annotations

import math
from datetime import date, timedelta

from app.providers.base import RateObservation

SOURCE_LABEL = "Mock 일별 시계열 (실제 환율 아님)"

BASELINES = {
    "USD_KRW": 1380.0,
    "EUR_KRW": 1490.0,
    "JPY_KRW": 920.0,
    "CNY_KRW": 195.0,
}


class MockExchangeProvider:
    name = "mock"
    is_mock = True

    def fetch_history(self, pair: str, start: date, end: date) -> list[RateObservation]:
        baseline = BASELINES.get(pair, 1300.0)
        points: list[RateObservation] = []
        current = start
        index = 0
        while current <= end:
            if current.weekday() < 5:
                wave = 18 * math.sin(index / 12) + 9 * math.sin(index / 37)
                drift = index * 0.04
                value = baseline + wave + drift
                points.append(
                    RateObservation(
                        pair=pair,
                        observed_at=current,
                        value=round(value, 4),
                        source=SOURCE_LABEL,
                        is_mock=True,
                    )
                )
                index += 1
            current += timedelta(days=1)
        return points
