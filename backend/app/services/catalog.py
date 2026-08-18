from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Indicator

PAIR_USD_KRW = "USD_KRW"
PAIR_EUR_KRW = "EUR_KRW"
PAIR_JPY_KRW = "JPY_KRW"
PAIR_CNY_KRW = "CNY_KRW"
SUPPORTED_PAIRS = (PAIR_USD_KRW, PAIR_EUR_KRW, PAIR_JPY_KRW, PAIR_CNY_KRW)


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    name: str
    category: str
    unit: str
    unit_label: str
    frequency: str
    source: str
    extra: dict


EXCHANGE_SPECS: dict[str, IndicatorSpec] = {
    PAIR_USD_KRW: IndicatorSpec(
        code=PAIR_USD_KRW,
        name="달러-원 환율",
        category="exchange_rate",
        unit="KRW/USD",
        unit_label="1달러당 원화",
        frequency="daily",
        source="Frankfurter (ECB)",
        extra={
            "base_currency": "USD",
            "quote_currency": "KRW",
            "display_scale": 1,
            "source_scale": 1,
        },
    ),
    PAIR_EUR_KRW: IndicatorSpec(
        code=PAIR_EUR_KRW,
        name="유로-원 환율",
        category="exchange_rate",
        unit="KRW/EUR",
        unit_label="1유로당 원화",
        frequency="daily",
        source="Frankfurter (ECB)",
        extra={
            "base_currency": "EUR",
            "quote_currency": "KRW",
            "display_scale": 1,
            "source_scale": 1,
        },
    ),
    PAIR_JPY_KRW: IndicatorSpec(
        code=PAIR_JPY_KRW,
        name="엔-원 환율",
        category="exchange_rate",
        unit="KRW/100JPY",
        unit_label="100엔당 원화",
        frequency="daily",
        source="Frankfurter (ECB)",
        extra={
            "base_currency": "JPY",
            "quote_currency": "KRW",
            "display_scale": 100,
            "source_scale": 1,
        },
    ),
    PAIR_CNY_KRW: IndicatorSpec(
        code=PAIR_CNY_KRW,
        name="위안-원 환율",
        category="exchange_rate",
        unit="KRW/CNY",
        unit_label="1위안당 원화",
        frequency="daily",
        source="Frankfurter (ECB)",
        extra={
            "base_currency": "CNY",
            "quote_currency": "KRW",
            "display_scale": 1,
            "source_scale": 1,
        },
    ),
}


def parse_extra(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def seed_indicators(db: Session) -> None:
    existing = {row.code for row in db.scalars(select(Indicator)).all()}
    for spec in EXCHANGE_SPECS.values():
        if spec.code in existing:
            continue
        db.add(
            Indicator(
                code=spec.code,
                name=spec.name,
                category=spec.category,
                unit=spec.unit,
                unit_label=spec.unit_label,
                frequency=spec.frequency,
                source=spec.source,
                extra=json.dumps(spec.extra, ensure_ascii=False),
            )
        )
    db.commit()


def get_indicator(db: Session, code: str) -> Indicator | None:
    return db.scalar(select(Indicator).where(Indicator.code == code))


def require_pair(code: str) -> str:
    normalized = code.upper().replace("/", "_").replace("-", "_")
    if normalized not in EXCHANGE_SPECS:
        raise ValueError(f"Unsupported pair: {code}")
    return normalized
