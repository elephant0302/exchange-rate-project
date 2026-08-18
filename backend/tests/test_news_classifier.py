from app.providers.news.classifier import (
    DIRECTION_KRW_STRONG,
    DIRECTION_KRW_WEAK,
    DIRECTION_NEUTRAL,
    IMPORTANCE_HIGH,
    IMPORTANCE_MEDIUM,
    classify_direction,
    classify_importance,
    extract_keywords,
    infer_pair,
    is_fx_related,
)


def test_direction_krw_weak() -> None:
    assert classify_direction("달러 강세로 원/달러 환율 상승") == DIRECTION_KRW_WEAK


def test_direction_krw_strong() -> None:
    assert classify_direction("원화 강세와 달러 약세가 동시에 관측") == DIRECTION_KRW_STRONG


def test_direction_conflict_is_neutral() -> None:
    assert classify_direction("원화 강세와 달러 강세가 혼재") == DIRECTION_NEUTRAL


def test_importance_high_for_fomc() -> None:
    assert classify_importance("연준 FOMC 기준금리 결정") == IMPORTANCE_HIGH


def test_importance_medium_for_inflation() -> None:
    assert classify_importance("미국 물가와 고용지표 발표") == IMPORTANCE_MEDIUM


def test_keywords_and_pair() -> None:
    text = "일본은행과 엔화, 원유 가격"
    assert "원유 가격" in extract_keywords(text) or "원유" in extract_keywords(text)
    assert infer_pair(text) == "JPY_KRW"


def test_infer_pair_cny() -> None:
    assert infer_pair("위안화와 중국인민은행") == "CNY_KRW"


def test_infer_pair_prefers_cny_over_usd_when_both_mentioned() -> None:
    assert infer_pair("위안-달러 6.7411위안") == "CNY_KRW"


def test_fx_related_filter() -> None:
    assert is_fx_related("원/달러 환율과 연준")
    assert not is_fx_related("오늘 축구 경기 결과")
