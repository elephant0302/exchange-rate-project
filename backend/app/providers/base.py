from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class RateObservation:
    pair: str
    observed_at: date
    value: float
    source: str
    is_mock: bool = False


@dataclass(frozen=True)
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str
    pair: str | None
    direction: str
    importance: str
    keywords: list[str]
    is_mock: bool = False


@dataclass(frozen=True)
class ForecastPoint:
    target_at: date
    predicted_value: float
    lower_bound: float
    upper_bound: float


@dataclass(frozen=True)
class ForecastResult:
    available: bool
    pair: str
    points: list[ForecastPoint]
    model_name: str | None = None
    confidence_level: float = 0.95
    trained_from: date | None = None
    trained_to: date | None = None
    mae: float | None = None
    rmse: float | None = None
    unavailable_reason: str | None = None
    comparisons: dict[str, dict[str, float]] = field(default_factory=dict)


class ExchangeRateProvider(Protocol):
    name: str
    is_mock: bool

    def fetch_history(self, pair: str, start: date, end: date) -> list[RateObservation]:
        ...


class NewsProvider(Protocol):
    name: str
    is_mock: bool

    def fetch_news(
        self,
        pair: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[NewsArticle]:
        ...


class ForecastProvider(Protocol):
    name: str

    def generate(
        self,
        pair: str,
        dates: list[date],
        values: list[float],
        horizon: int = 30,
    ) -> ForecastResult:
        ...


class NewsSummarizer(Protocol):
    """Hook for a future local or remote summarizer. Not used as a hard dependency."""

    def summarize(self, title: str, snippet: str) -> str:
        ...


class PassthroughSummarizer:
    def summarize(self, title: str, snippet: str) -> str:
        text = (snippet or title or "").strip()
        return text[:280]
