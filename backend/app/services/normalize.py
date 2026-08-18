from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dateutil.relativedelta import relativedelta


PERIOD_KEYS = ("1M", "3M", "6M", "1Y", "ALL")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_display_value(
    raw_value: float,
    display_scale: int | float = 1,
    source_scale: int | float = 1,
) -> float:
    """Convert a source quote to the dashboard display unit.

    JPY source quotes are typically 1엔당 원화. The dashboard shows 100엔당 원화,
    so display_scale=100 and source_scale=1 yields value * 100.
    """
    if source_scale == 0:
        raise ValueError("source_scale must not be zero")
    return float(raw_value) * (float(display_scale) / float(source_scale))


def period_start(period: str, end: date | None = None) -> date | None:
    key = period.upper()
    if key not in PERIOD_KEYS:
        raise ValueError(f"Unsupported period: {period}")
    if key == "ALL":
        return None
    end = end or date.today()
    mapping = {
        "1M": relativedelta(months=1),
        "3M": relativedelta(months=3),
        "6M": relativedelta(months=6),
        "1Y": relativedelta(years=1),
    }
    return end - mapping[key]


def daily_returns(values: list[float]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(values, values[1:]):
        if previous == 0:
            continue
        returns.append((current - previous) / previous)
    return returns


def realized_volatility(values: list[float]) -> float | None:
    """Annualized-ish daily vol as percent of the mean (sample std of daily returns)."""
    series = daily_returns(values)
    if len(series) < 2:
        return None
    mean = sum(series) / len(series)
    variance = sum((item - mean) ** 2 for item in series) / (len(series) - 1)
    return float(variance**0.5)


def change_amount(current: float, previous: float | None) -> float | None:
    if previous is None:
        return None
    return current - previous


def change_pct(current: float, previous: float | None) -> float | None:
    if previous in (None, 0):
        return None
    return (current - previous) / previous


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid"}
    ]
    cleaned = parts._replace(
        scheme=parts.scheme.lower(),
        netloc=parts.netloc.lower(),
        query=urlencode(query, doseq=True),
        fragment="",
    )
    return urlunsplit(cleaned).rstrip("/")


def clip_summary(text: str, limit: int = 280) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"
