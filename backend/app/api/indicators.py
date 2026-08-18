from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Indicator
from app.schemas.common import Envelope, IndicatorOut, ResponseMeta
from app.services.catalog import seed_indicators

router = APIRouter()


@router.get("/indicators", response_model=Envelope[list[IndicatorOut]])
def list_indicators(db: Session = Depends(get_db)) -> Envelope[list[IndicatorOut]]:
    seed_indicators(db)
    rows = list(db.scalars(select(Indicator).order_by(Indicator.id.asc())).all())
    return Envelope(
        data=[IndicatorOut.model_validate(row) for row in rows],
        meta=ResponseMeta(source="local catalog", is_mock=False),
    )
