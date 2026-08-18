from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.providers.base import NewsArticle
from app.providers.news.classifier import (
    DIRECTION_KRW_STRONG,
    DIRECTION_KRW_WEAK,
    DIRECTION_NEUTRAL,
    IMPORTANCE_HIGH,
    IMPORTANCE_LOW,
    IMPORTANCE_MEDIUM,
)

SOURCE_LABEL = "Mock 샘플 헤드라인 (실제 기사 아님)"


class MockNewsProvider:
    name = "mock"
    is_mock = True

    def fetch_news(
        self,
        pair: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[NewsArticle]:
        now = datetime.now(timezone.utc)
        samples = [
            (
                "[Mock] 샘플: 연준 FOMC 경계감 — 실제 기사가 아닙니다",
                "https://www.federalreserve.gov/monetarypolicy/fomc.htm",
                DIRECTION_KRW_WEAK,
                IMPORTANCE_HIGH,
                "USD_KRW",
                ["연준", "fomc"],
                "샘플 설명입니다. 실제 뉴스 수집이 실패했을 때 화면 흐름을 확인하기 위한 예시입니다.",
            ),
            (
                "[Mock] 샘플: 한국은행 기준금리 관련 코멘트 — 실제 기사가 아닙니다",
                "https://www.bok.or.kr/portal/main/main.do",
                DIRECTION_NEUTRAL,
                IMPORTANCE_HIGH,
                "USD_KRW",
                ["한국은행", "기준금리"],
                "샘플 설명입니다. 영향 방향을 단정하지 않습니다.",
            ),
            (
                "[Mock] 샘플: 유로존 물가 지표 점검 — 실제 기사가 아닙니다",
                "https://www.ecb.europa.eu/stats/html/index.en.html",
                DIRECTION_KRW_STRONG,
                IMPORTANCE_MEDIUM,
                "EUR_KRW",
                ["물가"],
                "샘플 설명입니다. ECB 통계 페이지로 연결되는 예시 링크입니다.",
            ),
            (
                "[Mock] 샘플: 엔화와 일본은행 정책 관측 — 실제 기사가 아닙니다",
                "https://www.boj.or.jp/en/index.htm",
                DIRECTION_NEUTRAL,
                IMPORTANCE_MEDIUM,
                "JPY_KRW",
                ["수출"],
                "샘플 설명입니다. 실제 환율 움직임과 무관한 예시입니다.",
            ),
            (
                "[Mock] 샘플: 위안화와 중국인민은행 관측 — 실제 기사가 아닙니다",
                "https://www.pbc.gov.cn/",
                DIRECTION_NEUTRAL,
                IMPORTANCE_MEDIUM,
                "CNY_KRW",
                ["위안화"],
                "샘플 설명입니다. 위안-원 선택 시 확인용 예시입니다.",
            ),
            (
                "[Mock] 샘플: 원유 가격과 무역수지 점검 — 실제 기사가 아닙니다",
                "https://www.imf.org/en/Home",
                DIRECTION_KRW_WEAK,
                IMPORTANCE_LOW,
                "USD_KRW",
                ["원유 가격", "무역수지"],
                "샘플 설명입니다. Mock 모드에서만 표시됩니다.",
            ),
        ]
        historical = [
            (45, "[Mock] 45일 전 샘플: 무역수지와 환율 — 실제 기사가 아닙니다"),
            (120, "[Mock] 120일 전 샘플: 연준 금리 관측 — 실제 기사가 아닙니다"),
            (200, "[Mock] 200일 전 샘플: 한국은행 기준금리 — 실제 기사가 아닙니다"),
            (400, "[Mock] 400일 전 샘플: 달러-원 변동 — 실제 기사가 아닙니다"),
        ]
        articles: list[NewsArticle] = []
        for index, item in enumerate(samples):
            title, url, direction, importance, item_pair, keywords, summary = item
            if pair and item_pair != pair:
                continue
            published = now - timedelta(days=index + 1)
            if start and published.date() < start:
                continue
            if end and published.date() > end:
                continue
            articles.append(
                NewsArticle(
                    title=title,
                    url=url,
                    source=SOURCE_LABEL,
                    published_at=published,
                    summary=summary,
                    pair=item_pair,
                    direction=direction,
                    importance=importance,
                    keywords=keywords,
                    is_mock=True,
                )
            )
        for offset, title in historical:
            published = now - timedelta(days=offset)
            if start and published.date() < start:
                continue
            if end and published.date() > end:
                continue
            if pair and pair != "USD_KRW":
                continue
            articles.append(
                NewsArticle(
                    title=title,
                    url="https://www.bok.or.kr/portal/main/main.do",
                    source=SOURCE_LABEL,
                    published_at=published,
                    summary="과거 구간 매핑 확인용 샘플이며 실제 기사가 아닙니다.",
                    pair="USD_KRW",
                    direction=DIRECTION_NEUTRAL,
                    importance=IMPORTANCE_MEDIUM,
                    keywords=["환율"],
                    is_mock=True,
                )
            )
        return articles
