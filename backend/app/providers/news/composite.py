from __future__ import annotations

from datetime import date

from app.providers.base import NewsArticle
from app.providers.news.historical import HistoricalNewsProvider
from app.providers.news.rss import RssNewsProvider


class CompositeNewsProvider:
    """Recent RSS plus dated historical backfill."""

    name = "rss+historical"
    is_mock = False

    def __init__(self, feed_urls: list[str]) -> None:
        self.rss = RssNewsProvider(feed_urls=feed_urls)
        self.historical = HistoricalNewsProvider()

    def fetch_news(
        self,
        pair: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[NewsArticle]:
        articles = list(self.rss.fetch_news(pair=pair))
        if start and end:
            articles.extend(self.historical.fetch_range(pair, start, end))
        return articles
