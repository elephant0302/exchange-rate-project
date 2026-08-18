from datetime import date

import pytest

from app.services.normalize import (
    change_amount,
    change_pct,
    normalize_url,
    period_start,
    realized_volatility,
    to_display_value,
)


def test_jpy_100_yen_conversion() -> None:
    assert to_display_value(8.8674, display_scale=100, source_scale=1) == pytest.approx(886.74)


def test_usd_passthrough() -> None:
    assert to_display_value(1411.91, display_scale=1, source_scale=1) == pytest.approx(1411.91)


def test_source_scale_guard() -> None:
    with pytest.raises(ValueError):
        to_display_value(1.0, display_scale=100, source_scale=0)


def test_period_filter_months() -> None:
    end = date(2026, 8, 18)
    assert period_start("1M", end) == date(2026, 7, 18)
    assert period_start("3M", end) == date(2026, 5, 18)
    assert period_start("6M", end) == date(2026, 2, 18)
    assert period_start("1Y", end) == date(2025, 8, 18)
    assert period_start("ALL", end) is None


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        period_start("2Y")


def test_change_metrics() -> None:
    assert change_amount(1412.0, 1400.0) == pytest.approx(12.0)
    assert change_pct(1412.0, 1400.0) == pytest.approx(12.0 / 1400.0)
    assert change_pct(1412.0, 0) is None


def test_volatility_empty() -> None:
    assert realized_volatility([100.0]) is None
    vol = realized_volatility([100.0, 101.0, 99.5, 102.0])
    assert vol is not None and vol > 0


def test_normalize_url_strips_tracking() -> None:
    raw = "https://News.Example.com/a?utm_source=rss&id=1#frag"
    assert normalize_url(raw) == "https://news.example.com/a?id=1"
