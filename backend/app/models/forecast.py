from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint(
            "indicator_id",
            "target_at",
            "created_at",
            name="uq_forecast_indicator_target_created",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"), index=True)
    target_at: Mapped[date] = mapped_column(Date, index=True)
    predicted_value: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.95)
    model_name: Mapped[str] = mapped_column(String(64))
    trained_from: Mapped[date] = mapped_column(Date)
    trained_to: Mapped[date] = mapped_column(Date)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    horizon_days: Mapped[int] = mapped_column(default=30)
    is_mock: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    indicator = relationship("Indicator", back_populates="forecasts")
