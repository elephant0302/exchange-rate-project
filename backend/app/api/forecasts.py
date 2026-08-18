from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import parse_horizon, parse_pair
from app.database import get_db
from app.schemas.common import Envelope
from app.schemas.forecast import ForecastOut
from app.services.query import forecasts

router = APIRouter()


@router.get("/forecasts", response_model=Envelope[ForecastOut])
def get_forecasts(
    pair: str = Depends(parse_pair),
    horizon: int = Depends(parse_horizon),
    db: Session = Depends(get_db),
) -> Envelope[ForecastOut]:
    data, meta = forecasts(db, pair, horizon)
    return Envelope(data=data, meta=meta)
