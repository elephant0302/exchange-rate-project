from fastapi import HTTPException, Query

from app.services.catalog import SUPPORTED_PAIRS, require_pair
from app.services.normalize import PERIOD_KEYS


def parse_pair(pair: str = Query("USD_KRW")) -> str:
    try:
        return require_pair(pair)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"pair must be one of {', '.join(SUPPORTED_PAIRS)}",
        ) from exc


def parse_period(period: str = Query("1Y")) -> str:
    key = period.upper()
    if key not in PERIOD_KEYS:
        raise HTTPException(status_code=422, detail=f"period must be one of {', '.join(PERIOD_KEYS)}")
    return key


def parse_horizon(horizon: int = Query(30)) -> int:
    if horizon not in (7, 30):
        raise HTTPException(status_code=422, detail="horizon must be 7 or 30")
    return horizon
