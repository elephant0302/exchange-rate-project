from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    source: str
    last_updated_at: datetime | None = None
    unit: str | None = None
    unit_label: str | None = None
    frequency: str = "daily"
    is_mock: bool = False
    warnings: list[str] = Field(default_factory=list)
    pair: str | None = None


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class HealthResponse(BaseModel):
    status: str
    database: str
    scheduler: bool
    providers: dict[str, str]
    environment: str


class IndicatorOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    unit: str
    unit_label: str
    frequency: str
    source: str

    model_config = {"from_attributes": True}


class CollectionStatusOut(BaseModel):
    job_name: str
    status: str
    source: str
    message: str
    is_mock: bool
    last_run_at: datetime | None
    last_success_at: datetime | None

    model_config = {"from_attributes": True}
