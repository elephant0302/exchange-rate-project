from datetime import date, timedelta

from app.providers.forecast.statistical import (
    ModelScore,
    StatisticalForecastProvider,
    _pick_model,
    next_business_days,
    recent_drift,
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


def test_forecast_interval_generation() -> None:
    dates, values = _series(120)
    result = StatisticalForecastProvider().generate("USD_KRW", dates, values, horizon=30)
    assert result.available is True
    assert result.model_name is not None
    assert result.model_name.startswith("ARIMA") or result.model_name in {"Naive", "Drift", "LocalMean"}
    assert result.mae is not None and result.rmse is not None
    assert len(result.points) == 30
    first = result.points[0]
    last = result.points[-1]
    assert first.lower_bound <= first.predicted_value <= first.upper_bound
    assert last.lower_bound <= last.predicted_value <= last.upper_bound
    assert (last.upper_bound - last.lower_bound) >= (first.upper_bound - first.lower_bound)
    assert result.trained_from == dates[0]
    assert result.trained_to == dates[-1]
    assert set(result.comparisons) >= {"Naive", "LocalMean", "Drift"}


def test_recent_drift_uses_short_window() -> None:
    old_down = [1400.0 - index for index in range(80)]
    recent_up = [1320.0 + index * 2 for index in range(21)]
    series = [*old_down, *recent_up]
    import numpy as np

    assert recent_drift(np.asarray(series, dtype=float)) > 0


def test_return_volatility_is_positive() -> None:
    import numpy as np

    values = np.array([1300 + ((-1) ** index) * 3 + index * 0.1 for index in range(80)], dtype=float)
    assert return_volatility(values) > 0


def test_pick_model_prefers_simpler_when_close() -> None:
    chosen = _pick_model(
        [
            ModelScore("ARIMA(1,1,1)", 1.00, 1.20),
            ModelScore("Naive", 1.02, 1.25),
            ModelScore("Drift", 1.10, 1.30),
        ]
    )
    assert chosen.name == "Naive"


def test_next_business_days_skips_weekend() -> None:
    days = next_business_days(date(2026, 8, 14), 3)  # Friday
    assert days[0] == date(2026, 8, 17)
    assert all(day.weekday() < 5 for day in days)
