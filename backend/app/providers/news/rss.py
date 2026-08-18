from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import mktime

import feedparser

from app.http import create_client
from app.providers.base import NewsArticle, PassthroughSummarizer
from app.providers.news.classifier import (
    classify_direction,
    classify_importance,
    extract_keywords,
    infer_pair,
    is_fx_related,
)
from app.services.normalize import clip_summary

logger = logging.getLogger(__name__)


def _published_at(entry) -> datetime:
    if getattr(entry, "published_parsed", None):
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    if getattr(entry, "published", None):
        try:
            parsed = parsedate_to_datetime(entry.published)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


def _source_name(entry, feed_title: str) -> str:
    source = getattr(entry, "source", None)
    if source and getattr(source, "title", None):
        return source.title
    return feed_title or "RSS"


class RssNewsProvider:
    name = "rss"
    is_mock = False

    def __init__(self, feed_urls: list[str]) -> None:
        self.feed_urls = feed_urls
        self.summarizer = PassthroughSummarizer()

    def fetch_news(
        self,
        pair: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[NewsArticle]:
        _ = start, end
        articles: list[NewsArticle] = []
        with create_client() as client:
            for url in self.feed_urls:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                except Exception as exc:
                    logger.warning("RSS fetch failed for %s: %s", url, exc)
                    continue
                feed_title = getattr(feed.feed, "title", "") or "RSS"
                for entry in feed.entries[:40]:
                    title = (getattr(entry, "title", "") or "").strip()
                    link = (getattr(entry, "link", "") or "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                    if not title or not link:
                        continue
                    blob = f"{title} {summary}"
                    if feed_title.lower().startswith("bbc") and not is_fx_related(blob):
                        continue
                    inferred = infer_pair(blob, fallback=pair or "USD_KRW")
                    articles.append(
                        NewsArticle(
                            title=title,
                            url=link,
                            source=_source_name(entry, feed_title),
                            published_at=_published_at(entry),
                            summary=clip_summary(self.summarizer.summarize(title, summary)),
                            pair=inferred,
                            direction=classify_direction(blob),
                            importance=classify_importance(blob),
                            keywords=extract_keywords(blob),
                            is_mock=False,
                        )
                    )
        logger.info("Fetched %s RSS articles", len(articles))
        return articles
