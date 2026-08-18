from datetime import date, timedelta

from app.models import Event, Observation
from app.providers.base import NewsArticle, RateObservation
from app.providers.exchange.mock import MockExchangeProvider
from app.services.catalog import get_indicator
from app.services.ingest import _save_news, _save_observations, ingest_exchange_rates
from app.services.normalize import utcnow


def test_duplicate_observations_are_skipped(db) -> None:
    indicator = get_indicator(db, "USD_KRW")
    assert indicator is not None
    point = RateObservation(
        pair="USD_KRW",
        observed_at=date(2026, 8, 17),
        value=1411.91,
        source="test",
        is_mock=True,
    )
    assert _save_observations(db, indicator.id, [point]) == 1
    assert _save_observations(db, indicator.id, [point]) == 0
    count = db.query(Observation).filter(Observation.indicator_id == indicator.id).count()
    assert count == 1


def test_duplicate_news_by_normalized_url(db) -> None:
    article = NewsArticle(
        title="Sample",
        url="https://Example.com/a?utm_source=rss",
        source="test",
        published_at=utcnow(),
        summary="desc",
        pair="USD_KRW",
        direction="neutral",
        importance="low",
        keywords=[],
        is_mock=True,
    )
    duplicate = NewsArticle(
        title="Sample copy",
        url="https://example.com/a",
        source="test",
        published_at=utcnow(),
        summary="desc",
        pair="USD_KRW",
        direction="neutral",
        importance="low",
        keywords=[],
        is_mock=True,
    )
    assert _save_news(db, [article]) == 1
    assert _save_news(db, [duplicate]) == 0
    assert db.query(Event).count() == 1


def test_external_failure_falls_back_to_mock(db, monkeypatch) -> None:
    class Boom:
        name = "frankfurter"
        is_mock = False

        def fetch_history(self, pair, start, end):
            raise RuntimeError("provider down")

    from app.config import get_settings
    from app.services import ingest as ingest_mod

    monkeypatch.setattr(ingest_mod, "build_exchange_provider", lambda settings: Boom())
    settings = get_settings()
    result = ingest_exchange_rates(db, settings, pairs=("USD_KRW",))
    assert result["is_mock"] is True
    assert db.query(Observation).count() > 0
    assert any("실패" in warning for warning in result["warnings"])


def test_mock_provider_generates_business_days() -> None:
    start = date(2026, 7, 1)
    end = date(2026, 7, 31)
    points = MockExchangeProvider().fetch_history("JPY_KRW", start, end)
    assert points
    assert all(point.observed_at.weekday() < 5 for point in points)
    assert all(point.is_mock for point in points)
    assert (end - start) <= timedelta(days=40)
