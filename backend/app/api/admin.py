from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.common import CollectionStatusOut, Envelope, ResponseMeta
from app.services.ingest import generate_forecasts, refresh_all
from app.services.status import list_statuses

router = APIRouter()


def _ensure_admin() -> None:
    if not get_settings().admin_api_enabled:
        raise HTTPException(
            status_code=403,
            detail="Admin API is disabled. Set ADMIN_API_ENABLED=true for development only.",
        )


@router.post("/admin/refresh")
def admin_refresh(db: Session = Depends(get_db)) -> dict:
    _ensure_admin()
    return refresh_all(db)


@router.post("/admin/forecast")
def admin_forecast(db: Session = Depends(get_db)) -> dict:
    _ensure_admin()
    return generate_forecasts(db)


@router.get("/admin/status", response_model=Envelope[list[CollectionStatusOut]])
def admin_status(db: Session = Depends(get_db)) -> Envelope[list[CollectionStatusOut]]:
    rows = list_statuses(db)
    return Envelope(
        data=[CollectionStatusOut.model_validate(row) for row in rows],
        meta=ResponseMeta(source="local", is_mock=False),
    )
