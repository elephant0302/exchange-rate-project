from datetime import date, datetime, timedelta, timezone

from app.models import Event
from app.providers.news.historical import (
    google_news_window_url,
    month_windows,
    parse_gdelt_datetime,
    query_for_pair,
)
from app.services.catalog import get_indicator
from app.services.query import news_list


def test_month_windows_split_range() -> None:
    windows = month_windows(date(2026, 1, 15), date(2026, 3, 10))
    assert windows == [
        (date(2026, 1, 15), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
        (date(2026, 3, 1), date(2026, 3, 10)),
    ]


def test_google_news_window_uses_after_before() -> None:
    url = google_news_window_url("환율", date(2025, 3, 1), date(2025, 3, 31))
    assert "after%3A2025-03-01" in url or "after:2025-03-01" in url
    assert "before%3A2025-04-01" in url or "before:2025-04-01" in url


def test_parse_gdelt_datetime() -> None:
    parsed = parse_gdelt_datetime("20250817T153000Z")
    assert parsed == datetime(2025, 8, 17, 15, 30, tzinfo=timezone.utc)


def test_news_list_filters_by_period(db) -> None:
    indicator = get_indicator(db, "USD_KRW")
    assert indicator is not None
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            Event(
                indicator_id=indicator.id,
                title="recent",
                url="https://example.com/recent",
                normalized_url="https://example.com/recent",
                source="test",
                published_at=now - timedelta(days=3),
                direction="neutral",
                importance="low",
                summary="recent",
                keywords="환율",
                is_mock=True,
            ),
            Event(
                indicator_id=indicator.id,
                title="old",
                url="https://example.com/old",
                normalized_url="https://example.com/old",
                source="test",
                published_at=now - timedelta(days=200),
                direction="neutral",
                importance="low",
                summary="old",
                keywords="환율",
                is_mock=True,
            ),
        ]
    )
    db.commit()
    month_items, _ = news_list(db, "USD_KRW", limit=50, period="1M")
    year_items, _ = news_list(db, "USD_KRW", limit=50, period="1Y")
    assert [item.title for item in month_items] == ["recent"]
    assert {item.title for item in year_items} == {"recent", "old"}


def test_query_for_pair_uses_cny_terms() -> None:
    query = query_for_pair("CNY_KRW")
    assert "위안화" in query
    assert "인민은행" in query


def test_news_list_includes_cny_keyword_even_if_tagged_usd(db) -> None:
    usd = get_indicator(db, "USD_KRW")
    assert usd is not None
    now = datetime.now(timezone.utc)
    db.add(
        Event(
            indicator_id=usd.id,
            title="관세전쟁, 환율전쟁으로 확전…中, 위안화 사상 최저치로 낮췄다",
            url="https://example.com/cny",
            normalized_url="https://example.com/cny",
            source="test",
            published_at=now - timedelta(days=2),
            direction="neutral",
            importance="medium",
            summary="위안화",
            keywords="환율",
            is_mock=True,
        )
    )
    db.commit()
    items, _ = news_list(db, "CNY_KRW", limit=50, period="1M")
    assert any("위안화" in item.title for item in items)


def test_news_list_keeps_older_months_when_limit_is_small(db) -> None:
    indicator = get_indicator(db, "USD_KRW")
    assert indicator is not None
    now = datetime.now(timezone.utc)
    for index in range(8):
        published = now - timedelta(days=30 * index + 2)
        db.add(
            Event(
                indicator_id=indicator.id,
                title=f"month-{published.strftime('%Y-%m')}-{index}",
                url=f"https://example.com/month-{index}",
                normalized_url=f"https://example.com/month-{index}",
                source="test",
                published_at=published,
                direction="neutral",
                importance="low",
                summary="환율",
                keywords="환율",
                is_mock=True,
            )
        )
    db.commit()
    items, _ = news_list(db, "USD_KRW", limit=4, period="1Y")
    months = {item.published_at.strftime("%Y-%m") for item in items}
    assert len(items) == 4
    assert len(months) >= 4
