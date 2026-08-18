from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("normalized_url", name="uq_event_normalized_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int | None] = mapped_column(
        ForeignKey("indicators.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    normalized_url: Mapped[str] = mapped_column(String(1024), index=True)
    source: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    direction: Mapped[str] = mapped_column(String(32), default="neutral")
    importance: Mapped[str] = mapped_column(String(16), default="medium")
    summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    is_mock: Mapped[bool] = mapped_column(default=False)

    indicator = relationship("Indicator", back_populates="events")
