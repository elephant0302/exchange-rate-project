from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import parse_pair, parse_period
from app.database import get_db
from app.schemas.common import Envelope
from app.schemas.news import NewsItemOut
from app.services.query import news_list

router = APIRouter()


@router.get("/news", response_model=Envelope[list[NewsItemOut]])
def get_news(
    pair: str = Depends(parse_pair),
    period: str = Depends(parse_period),
    limit: int = Query(2000, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> Envelope[list[NewsItemOut]]:
    data, meta = news_list(db, pair, limit, period)
    return Envelope(data=data, meta=meta)
