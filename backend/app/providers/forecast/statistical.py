from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from statsmodels.tsa.arima.model import ARIMA

from app.providers.base import ForecastPoint, ForecastResult

logger = logging.getLogger(__name__)

MIN_OBSERVATIONS = 90
CONFIDENCE = 0.95
Z_95 = 1.96


@dataclass
class ModelScore:
    name: str
    mae: float
    rmse: float


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def next_business_days(start: date, count: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < count:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days.append(current)
    return days


def _naive_forecast(last: float, horizon: int, residual_std: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    center = np.full(horizon, last)
    steps = np.sqrt(np.arange(1, horizon + 1))
    width = Z_95 * residual_std * steps
    return center, center - width, center + width


def _drift_forecast(
    series: np.ndarray, horizon: int, residual_std: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    drift = float((series[-1] - series[0]) / max(len(series) - 1, 1))
    steps = np.arange(1, horizon + 1)
    center = series[-1] + drift * steps
    width = Z_95 * residual_std * np.sqrt(steps)
    return center, center - width, center + width


def _residual_std(actual: np.ndarray, predicted: np.ndarray) -> float:
    residuals = actual - predicted
    if len(residuals) < 2:
        return max(float(np.std(actual) or 1.0), 1.0)
    return max(float(np.std(residuals, ddof=1)), 1e-6)


class StatisticalForecastProvider:
    name = "statistical"

    def generate(
        self,
        pair: str,
        dates: list[date],
        values: list[float],
        horizon: int = 30,
    ) -> ForecastResult:
        if len(values) < MIN_OBSERVATIONS:
            return ForecastResult(
                available=False,
                pair=pair,
                points=[],
                unavailable_reason=(
                    f"예측에 필요한 일별 데이터가 부족합니다. "
                    f"최소 {MIN_OBSERVATIONS}영업일이 필요하지만 현재 {len(values)}일입니다."
                ),
            )

        series = np.asarray(values, dtype=float)
        validation_size = min(21, max(7, len(series) // 6))
        train = series[:-validation_size]
        valid = series[-validation_size:]

        candidates: list[tuple[ModelScore, np.ndarray]] = []

        naive_pred = np.full(len(valid), train[-1])
        candidates.append(
            (ModelScore("Naive", mae(valid, naive_pred), rmse(valid, naive_pred)), naive_pred)
        )

        drift = float((train[-1] - train[0]) / max(len(train) - 1, 1))
        drift_pred = train[-1] + drift * np.arange(1, len(valid) + 1)
        candidates.append(
            (ModelScore("Drift", mae(valid, drift_pred), rmse(valid, drift_pred)), drift_pred)
        )

        arima_pred = self._safe_arima_predict(train, len(valid))
        if arima_pred is not None:
            candidates.append(
                (
                    ModelScore("ARIMA(1,1,1)", mae(valid, arima_pred), rmse(valid, arima_pred)),
                    arima_pred,
                )
            )

        best_score, best_pred = min(candidates, key=lambda item: (item[0].mae, item[0].rmse))
        residual = _residual_std(valid, best_pred)

        try:
            center, lower, upper = self._forecast_full(best_score.name, series, horizon, residual)
        except Exception as exc:
            logger.exception("Forecast generation failed for %s", pair)
            return ForecastResult(
                available=False,
                pair=pair,
                points=[],
                unavailable_reason=f"모델 생성에 실패했습니다: {exc.__class__.__name__}",
            )

        targets = next_business_days(dates[-1], horizon)
        points = [
            ForecastPoint(
                target_at=target,
                predicted_value=round(float(center[index]), 4),
                lower_bound=round(float(lower[index]), 4),
                upper_bound=round(float(upper[index]), 4),
            )
            for index, target in enumerate(targets)
        ]
        return ForecastResult(
            available=True,
            pair=pair,
            points=points,
            model_name=best_score.name,
            confidence_level=CONFIDENCE,
            trained_from=dates[0],
            trained_to=dates[-1],
            mae=round(best_score.mae, 4),
            rmse=round(best_score.rmse, 4),
            comparisons={
                score.name: {"mae": round(score.mae, 4), "rmse": round(score.rmse, 4)}
                for score, _ in candidates
            },
        )

    def _safe_arima_predict(self, train: np.ndarray, steps: int) -> np.ndarray | None:
        try:
            fitted = ARIMA(train, order=(1, 1, 1)).fit()
            predicted = fitted.forecast(steps=steps)
            if predicted is None or len(predicted) != steps or np.any(~np.isfinite(predicted)):
                return None
            return np.asarray(predicted, dtype=float)
        except Exception as exc:
            logger.info("ARIMA validation skipped: %s", exc)
            return None

    def _forecast_full(
        self,
        model_name: str,
        series: np.ndarray,
        horizon: int,
        residual_std: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if model_name == "Naive":
            return _naive_forecast(float(series[-1]), horizon, residual_std)
        if model_name == "Drift":
            return _drift_forecast(series, horizon, residual_std)

        fitted = ARIMA(series, order=(1, 1, 1)).fit()
        forecasted = fitted.get_forecast(steps=horizon)
        center = np.asarray(forecasted.predicted_mean, dtype=float)
        conf = np.asarray(forecasted.conf_int(alpha=1 - CONFIDENCE), dtype=float)
        return center, conf[:, 0], conf[:, 1]
