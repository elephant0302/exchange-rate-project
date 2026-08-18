from datetime import date, timedelta

from app.providers.forecast.statistical import StatisticalForecastProvider, next_business_days


def _series(n: int, start: float = 1300.0) -> tuple[list[date], list[float]]:
    start_day = date(2025, 1, 2)
    dates: list[date] = []
    values: list[float] = []
    current = start_day
    value = start
    while len(values) < n:
        if current.weekday() < 5:
            dates.append(current)
            values.append(round(value, 4))
            value += 0.35
        current += timedelta(days=1)
    return dates, values


def test_forecast_requires_90_days() -> None:
    dates, values = _series(40)
    result = StatisticalForecastProvider().generate("USD_KRW", dates, values)
    assert result.available is False
    assert result.unavailable_reason is not None
    assert "90" in result.unavailable_reason
    assert result.points == []


def test_forecast_interval_generation() -> None:
    dates, values = _series(120)
    result = StatisticalForecastProvider().generate("USD_KRW", dates, values, horizon=30)
    assert result.available is True
    assert result.model_name in {"Naive", "Drift", "ARIMA(1,1,1)"}
    assert result.mae is not None and result.rmse is not None
    assert len(result.points) == 30
    first = result.points[0]
    assert first.lower_bound <= first.predicted_value <= first.upper_bound
    assert result.points[-1].lower_bound <= result.points[-1].upper_bound
    assert result.trained_from == dates[0]
    assert result.trained_to == dates[-1]


def test_next_business_days_skips_weekend() -> None:
    days = next_business_days(date(2026, 8, 14), 3)  # Friday
    assert days[0] == date(2026, 8, 17)
    assert all(day.weekday() < 5 for day in days)
