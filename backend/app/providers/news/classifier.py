from __future__ import annotations

import re

from app.services.catalog import PAIR_CNY_KRW, PAIR_EUR_KRW, PAIR_JPY_KRW, PAIR_USD_KRW

DIRECTION_KRW_STRONG = "krw_strong"
DIRECTION_KRW_WEAK = "krw_weak"
DIRECTION_NEUTRAL = "neutral"

IMPORTANCE_HIGH = "high"
IMPORTANCE_MEDIUM = "medium"
IMPORTANCE_LOW = "low"

DIRECTION_LABELS = {
    DIRECTION_KRW_STRONG: "원화 강세 가능성",
    DIRECTION_KRW_WEAK: "원화 약세 가능성",
    DIRECTION_NEUTRAL: "중립 또는 불명확",
}

IMPORTANCE_LABELS = {
    IMPORTANCE_HIGH: "높음",
    IMPORTANCE_MEDIUM: "보통",
    IMPORTANCE_LOW: "낮음",
}

HIGH_KEYWORDS = (
    "기준금리",
    "연준",
    "fomc",
    "한국은행",
    "federal reserve",
    "interest rate decision",
    "rate hike",
    "rate cut",
)

MEDIUM_KEYWORDS = (
    "물가",
    "고용지표",
    "고용",
    "관세",
    "무역수지",
    "외환보유액",
    "지정학적",
    "외국인 자금",
    "외국인",
    "수출",
    "원유 가격",
    "원유",
    "cpi",
    "payroll",
    "tariff",
    "inflation",
)

KRW_STRONG_HINTS = (
    "원화 강세",
    "달러 약세",
    "환율 하락",
    "원/달러 하락",
    "달러 약세",
    "won strengthens",
    "dollar weak",
    "원화값 상승",
)

KRW_WEAK_HINTS = (
    "원화 약세",
    "달러 강세",
    "환율 상승",
    "원/달러 상승",
    "강달러",
    "won weak",
    "dollar strong",
    "원화값 하락",
)

PAIR_HINTS = {
    PAIR_EUR_KRW: ("유로", "eur", "ecb", "유럽중앙은행"),
    PAIR_JPY_KRW: ("엔화", "엔-원", "jpy", "일본은행", "boj"),
    PAIR_CNY_KRW: (
        "위안화",
        "위안",
        "인민폐",
        "원/위안",
        "원·위안",
        "원-위안",
        "위안-원",
        "인민은행",
        "중국인민은행",
        "cny",
        "pboc",
        "yuan",
    ),
    PAIR_USD_KRW: ("달러", "usd", "연준", "fomc", "원/달러", "원달러"),
}

FX_HINTS = (
    "환율",
    "외환",
    "달러",
    "위안",
    "위안화",
    "원화",
    "연준",
    "fomc",
    "한국은행",
    "기준금리",
    "fx",
    "won",
    "dollar",
    "currency",
    "forex",
    "krw",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def classify_direction(text: str) -> str:
    blob = _normalize(text)
    strong = any(hint in blob for hint in KRW_STRONG_HINTS)
    weak = any(hint in blob for hint in KRW_WEAK_HINTS)
    if strong and not weak:
        return DIRECTION_KRW_STRONG
    if weak and not strong:
        return DIRECTION_KRW_WEAK
    return DIRECTION_NEUTRAL


def classify_importance(text: str) -> str:
    blob = _normalize(text)
    if any(keyword in blob for keyword in HIGH_KEYWORDS):
        return IMPORTANCE_HIGH
    if any(keyword in blob for keyword in MEDIUM_KEYWORDS):
        return IMPORTANCE_MEDIUM
    return IMPORTANCE_LOW


def extract_keywords(text: str) -> list[str]:
    blob = _normalize(text)
    found: list[str] = []
    for keyword in HIGH_KEYWORDS + MEDIUM_KEYWORDS:
        if keyword in blob and keyword not in found:
            found.append(keyword)
    return found[:8]


def infer_pair(text: str, fallback: str | None = PAIR_USD_KRW) -> str | None:
    blob = _normalize(text)
    scores = {
        pair: sum(1 for hint in hints if hint in blob)
        for pair, hints in PAIR_HINTS.items()
    }
    best_score = max(scores.values())
    if best_score > 0:
        winners = [pair for pair, score in scores.items() if score == best_score]
        if PAIR_USD_KRW in winners and len(winners) > 1:
            winners = [pair for pair in winners if pair != PAIR_USD_KRW]
        return winners[0]
    if any(hint in blob for hint in FX_HINTS):
        return fallback
    return fallback


def is_fx_related(text: str) -> bool:
    blob = _normalize(text)
    return any(hint in blob for hint in FX_HINTS + MEDIUM_KEYWORDS + HIGH_KEYWORDS)
