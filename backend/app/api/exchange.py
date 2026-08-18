from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import parse_pair, parse_period
from app.database import get_db
from app.schemas.common import Envelope
from app.schemas.exchange import HistoryOut, LatestRateOut
from app.services.query import history, latest_rate

router = APIRouter()


@router.get("/exchange-rates/latest", response_model=Envelope[LatestRateOut])
def get_latest(
    pair: str = Depends(parse_pair),
    period: str = Depends(parse_period),
    db: Session = Depends(get_db),
) -> Envelope[LatestRateOut]:
    data, meta = latest_rate(db, pair, period)
    return Envelope(data=data, meta=meta)


@router.get("/exchange-rates/history", response_model=Envelope[HistoryOut])
def get_history(
    pair: str = Depends(parse_pair),
    period: str = Depends(parse_period),
    db: Session = Depends(get_db),
) -> Envelope[HistoryOut]:
    data, meta = history(db, pair, period)
    return Envelope(data=data, meta=meta)
