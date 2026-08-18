from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NewsItemOut(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: datetime
    collected_at: datetime
    pair: str | None
    direction: str
    direction_label: str
    importance: str
    importance_label: str
    summary: str
    keywords: list[str]
    is_mock: bool

    model_config = {"from_attributes": True}
