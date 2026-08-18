from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote_plus

from dateutil.relativedelta import relativedelta

from app.http import create_client
from app.providers.base import NewsArticle, PassthroughSummarizer
from app.providers.news.classifier import (
    classify_direction,
    classify_importance,
    extract_keywords,
    infer_pair,
    is_fx_related,
)
from app.providers.news.rss import RssNewsProvider
from app.services.normalize import clip_summary

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_QUERY = (
    '환율 OR "원/달러" OR 위안화 OR "원/위안" OR 인민은행 OR 연준 OR FOMC '
    'OR "Bank of Korea" OR "Korean won" OR yuan'
)
PAIR_QUERIES = {
    "CNY_KRW": '위안화 OR "원/위안" OR "원·위안" OR yuan OR CNY OR 인민은행',
    "EUR_KRW": '유로 OR "원/유로" OR ECB OR 유럽중앙은행',
    "JPY_KRW": '엔화 OR "원/엔" OR 일본은행 OR BOJ',
    "USD_KRW": DEFAULT_QUERY,
}


def query_for_pair(pair: str | None) -> str:
    if pair and pair in PAIR_QUERIES:
        return PAIR_QUERIES[pair]
    return DEFAULT_QUERY


def month_windows(start: date, end: date) -> list[tuple[date, date]]:
    if start > end:
        return []
    windows: list[tuple[date, date]] = []
    current = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while current <= last:
        nxt = current + relativedelta(months=1)
        window_start = max(current, start)
        window_end = min(nxt - timedelta(days=1), end)
        windows.append((window_start, window_end))
        current = nxt
    return windows


def google_news_window_url(query: str, start: date, end: date) -> str:
    bounded = f"{query} after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}"
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(bounded)}&hl=ko&gl=KR&ceid=KR:ko"
    )


def parse_gdelt_datetime(raw: str) -> datetime:
    text = (raw or "").strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


class HistoricalNewsProvider:
    name = "historical"
    is_mock = False

    def __init__(self) -> None:
        self.summarizer = PassthroughSummarizer()

    def fetch_news(self, pair: str | None = None, start: date | None = None, end: date | None = None) -> list[NewsArticle]:
        end = end or date.today()
        start = start or (end - relativedelta(months=12))
        return self.fetch_range(pair, start, end)

    def fetch_range(self, pair: str | None, start: date, end: date) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for window_start, window_end in month_windows(start, end):
            articles.extend(self._fetch_google_window(pair, window_start, window_end))
            articles.extend(self._fetch_gdelt_window(pair, window_start, window_end))
        logger.info("Fetched %s historical articles from %s to %s", len(articles), start, end)
        return articles

    def _fetch_google_window(self, pair: str | None, start: date, end: date) -> list[NewsArticle]:
        url = google_news_window_url(query_for_pair(pair), start, end)
        provider = RssNewsProvider(feed_urls=[url])
        try:
            return provider.fetch_news(pair=pair)
        except Exception as exc:
            logger.warning("Dated Google News RSS failed %s..%s: %s", start, end, exc)
            return []

    def _fetch_gdelt_window(self, pair: str | None, start: date, end: date) -> list[NewsArticle]:
        params = {
            "query": query_for_pair(pair),
            "mode": "ArtList",
            "maxrecords": 40,
            "format": "json",
            "startdatetime": start.strftime("%Y%m%d000000"),
            "enddatetime": end.strftime("%Y%m%d235959"),
            "sort": "DateDesc",
        }
        try:
            with create_client() as client:
                response = client.get(GDELT_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("GDELT fetch failed %s..%s: %s", start, end, exc)
            return []

        rows = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []
        articles: list[NewsArticle] = []
        for row in rows:
            title = (row.get("title") or "").strip()
            url = (row.get("url") or "").strip()
            if not title or not url:
                continue
            summary = (row.get("seendate") or title).strip()
            blob = f"{title} {summary}"
            if not is_fx_related(blob):
                continue
            articles.append(
                NewsArticle(
                    title=title,
                    url=url,
                    source=str(row.get("domain") or "GDELT"),
                    published_at=parse_gdelt_datetime(str(row.get("seendate") or "")),
                    summary=clip_summary(self.summarizer.summarize(title, title)),
                    pair=infer_pair(blob, fallback=pair or "USD_KRW"),
                    direction=classify_direction(blob),
                    importance=classify_importance(blob),
                    keywords=extract_keywords(blob),
                    is_mock=False,
                )
            )
        return articles
