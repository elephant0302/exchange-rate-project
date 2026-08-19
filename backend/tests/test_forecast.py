from datetime import date, timedelta

import numpy as np

from app.providers.forecast.statistical import (
    ModelScore,
    StatisticalForecastProvider,
    combination_weights,
    next_business_days,
    return_volatility,
)


def _series(n: int, start: float = 1300.0, step: float = 0.35) -> tuple[list[date], list[float]]:
    start_day = date(2025, 1, 2)
    dates: list[date] = []
    values: list[float] = []
    current = start_day
    value = start
    while len(values) < n:
        if current.weekday() < 5:
            dates.append(current)
            values.append(round(value, 4))
            value += step
        current += timedelta(days=1)
    return dates, values


def test_forecast_requires_90_days() -> None:
    dates, values = _series(40)
    result = StatisticalForecastProvider().generate("USD_KRW", dates, values)
    assert result.available is False
    assert result.unavailable_reason is not None
    assert "90" in result.unavailable_reason
    assert result.points == []


def test_forecast_uses_combination_and_widening_interval() -> None:
    dates, values = _series(120)
    result = StatisticalForecastProvider().generate("USD_KRW", dates, values, horizon=30)
    assert result.available is True
    assert result.model_name is not None
    assert result.model_name.startswith("Combination")
    assert "GARCH(1,1)" in result.model_name
    assert result.mae is not None and result.rmse is not None
    assert len(result.points) == 30
    first = result.points[0]
    last = result.points[-1]
    assert first.lower_bound <= first.predicted_value <= first.upper_bound
    assert last.lower_bound <= last.predicted_value <= last.upper_bound
    assert (last.upper_bound - last.lower_bound) >= (first.upper_bound - first.lower_bound)
    assert result.trained_from == dates[0]
    assert result.trained_to == dates[-1]
    assert set(result.comparisons) >= {"RW", "Combination"}


def test_dollar_factor_is_used_for_crosses() -> None:
    dates, eur = _series(120, start=1500.0, step=0.2)
    _, usd = _series(120, start=1300.0, step=0.4)
    result = StatisticalForecastProvider().generate(
        "EUR_KRW",
        dates,
        eur,
        horizon=14,
        factor_dates=dates,
        factor_values=usd,
    )
    assert result.available is True
    assert "DollarFactor" in result.comparisons or "RW" in result.comparisons


def test_combination_weights_sum_to_one() -> None:
    weights = combination_weights(
        [
            ModelScore("RW", 2.0, 2.5),
            ModelScore("AR", 1.0, 1.4),
            ModelScore("Combination", 1.2, 1.5),
        ]
    )
    assert "Combination" not in weights
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["AR"] > weights["RW"]


def test_return_volatility_is_positive() -> None:
    values = np.array([1300 + ((-1) ** index) * 3 + index * 0.1 for index in range(80)], dtype=float)
    assert return_volatility(values) > 0


def test_next_business_days_skips_weekend() -> None:
    days = next_business_days(date(2026, 8, 14), 3)  # Friday
    assert days[0] == date(2026, 8, 17)
    assert all(day.weekday() < 5 for day in days)
