from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64), index=True)
    unit: Mapped[str] = mapped_column(String(64))
    unit_label: Mapped[str] = mapped_column(String(128))
    frequency: Mapped[str] = mapped_column(String(32), default="daily")
    source: Mapped[str] = mapped_column(String(128))
    extra: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    observations = relationship("Observation", back_populates="indicator")
    events = relationship("Event", back_populates="indicator")
    forecasts = relationship("Forecast", back_populates="indicator")
