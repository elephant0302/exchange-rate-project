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
DRIFT_WINDOW = 21
MEAN_WINDOW = 5
VOL_WINDOW = 63
FOLD_SIZE = 7
FOLDS = 3
ARIMA_ORDERS = ((1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 1))
# Prefer a simpler model unless a richer one is clearly better.
PARSIMONY = 1.03
COMPLEXITY = {"Naive": 0, "LocalMean": 1, "Drift": 2}


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


def recent_drift(series: np.ndarray, window: int = DRIFT_WINDOW) -> float:
    lookback = series[-min(window, len(series)) :]
    return float((lookback[-1] - lookback[0]) / max(len(lookback) - 1, 1))


def local_mean(series: np.ndarray, window: int = MEAN_WINDOW) -> float:
    return float(np.mean(series[-min(window, len(series)) :]))


def return_volatility(series: np.ndarray, window: int = VOL_WINDOW) -> float:
    if len(series) < 3:
        return 0.01
    returns = np.diff(series) / np.clip(series[:-1], 1e-6, None)
    sample = returns[-min(window, len(returns)) :]
    sigma = float(np.std(sample, ddof=1)) if len(sample) > 1 else float(np.std(sample))
    return max(sigma, 1e-4)


def _naive_path(last: float, horizon: int) -> np.ndarray:
    return np.full(horizon, last)


def _drift_path(series: np.ndarray, horizon: int) -> np.ndarray:
    last = float(series[-1])
    return last + recent_drift(series) * np.arange(1, horizon + 1)


def _mean_path(series: np.ndarray, horizon: int) -> np.ndarray:
    return np.full(horizon, local_mean(series))


def _interval(
    center: np.ndarray,
    residual_std: float,
    last_price: float,
    vol: float,
) -> tuple[np.ndarray, np.ndarray]:
    steps = np.sqrt(np.arange(1, len(center) + 1))
    from_holdout = Z_95 * residual_std * steps
    from_returns = Z_95 * last_price * vol * steps
    width = np.maximum(from_holdout, from_returns)
    lower = np.maximum(center - width, 0.01)
    upper = center + width
    return lower, upper


def _residual_std(actual: np.ndarray, predicted: np.ndarray) -> float:
    residuals = actual - predicted
    if len(residuals) < 2:
        return max(float(np.std(actual) or 1.0), 1.0)
    return max(float(np.std(residuals, ddof=1)), 1e-6)


def _validation_windows(length: int) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for fold in range(FOLDS):
        valid_end = length - (FOLDS - 1 - fold) * FOLD_SIZE
        valid_start = valid_end - FOLD_SIZE
        if valid_start < MIN_OBSERVATIONS // 2:
            continue
        windows.append((valid_start, valid_end))
    return windows


def _pick_model(scores: list[ModelScore]) -> ModelScore:
    best_mae = min(item.mae for item in scores)
    eligible = [item for item in scores if item.mae <= best_mae * PARSIMONY]
    return min(eligible, key=lambda item: (COMPLEXITY.get(item.name, 3), item.mae, item.rmse))


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
        scores, residual = self._score_candidates(series)
        if not scores:
            return ForecastResult(
                available=False,
                pair=pair,
                points=[],
                unavailable_reason="검증 구간을 만들 수 없어 예측을 생성하지 않았습니다.",
            )

        best = _pick_model(scores)
        try:
            center, lower, upper = self._forecast_full(best.name, series, horizon, residual)
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
            model_name=best.name,
            confidence_level=CONFIDENCE,
            trained_from=dates[0],
            trained_to=dates[-1],
            mae=round(best.mae, 4),
            rmse=round(best.rmse, 4),
            comparisons={
                score.name: {"mae": round(score.mae, 4), "rmse": round(score.rmse, 4)}
                for score in scores
            },
        )

    def _score_candidates(self, series: np.ndarray) -> tuple[list[ModelScore], float]:
        windows = _validation_windows(len(series))
        collected: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
            "Naive": [],
            "LocalMean": [],
            "Drift": [],
        }
        arima_order = self._select_arima_order(series[: windows[0][0]]) if windows else None
        arima_name = f"ARIMA{arima_order}" if arima_order else None
        if arima_name:
            collected[arima_name] = []

        for start, end in windows:
            train = series[:start]
            valid = series[start:end]
            collected["Naive"].append((_naive_path(float(train[-1]), len(valid)), valid))
            collected["LocalMean"].append((_mean_path(train, len(valid)), valid))
            collected["Drift"].append((_drift_path(train, len(valid)), valid))
            if arima_order and arima_name:
                predicted = self._safe_arima_predict(train, len(valid), arima_order)
                if predicted is not None:
                    collected[arima_name].append((predicted, valid))

        scores: list[ModelScore] = []
        residuals: list[float] = []
        for name, pairs in collected.items():
            if not pairs:
                continue
            actual = np.concatenate([valid for _, valid in pairs])
            predicted = np.concatenate([pred for pred, _ in pairs])
            scores.append(ModelScore(name, mae(actual, predicted), rmse(actual, predicted)))
            residuals.append(_residual_std(actual, predicted))
        residual = max(residuals) if residuals else 1.0
        return scores, residual

    def _select_arima_order(self, train: np.ndarray) -> tuple[int, int, int] | None:
        best_order: tuple[int, int, int] | None = None
        best_aic = float("inf")
        for order in ARIMA_ORDERS:
            try:
                fitted = ARIMA(train, order=order).fit()
                aic = float(fitted.aic)
                if np.isfinite(aic) and aic < best_aic:
                    best_aic = aic
                    best_order = order
            except Exception as exc:
                logger.info("ARIMA order %s skipped: %s", order, exc)
        return best_order

    def _safe_arima_predict(
        self,
        train: np.ndarray,
        steps: int,
        order: tuple[int, int, int],
    ) -> np.ndarray | None:
        try:
            fitted = ARIMA(train, order=order).fit()
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
        last = float(series[-1])
        vol = return_volatility(series)
        if model_name == "Naive":
            center = _naive_path(last, horizon)
            lower, upper = _interval(center, residual_std, last, vol)
            return center, lower, upper
        if model_name == "LocalMean":
            center = _mean_path(series, horizon)
            lower, upper = _interval(center, residual_std, last, vol)
            return center, lower, upper
        if model_name == "Drift":
            center = _drift_path(series, horizon)
            lower, upper = _interval(center, residual_std, last, vol)
            return center, lower, upper

        order = self._parse_arima_name(model_name) or (1, 1, 1)
        fitted = ARIMA(series, order=order).fit()
        forecasted = fitted.get_forecast(steps=horizon)
        center = np.asarray(forecasted.predicted_mean, dtype=float)
        conf = np.asarray(forecasted.conf_int(alpha=1 - CONFIDENCE), dtype=float)
        ret_lower, ret_upper = _interval(center, residual_std, last, vol)
        lower = np.minimum(conf[:, 0], ret_lower)
        upper = np.maximum(conf[:, 1], ret_upper)
        return center, np.maximum(lower, 0.01), upper

    @staticmethod
    def _parse_arima_name(name: str) -> tuple[int, int, int] | None:
        if not name.startswith("ARIMA(") or not name.endswith(")"):
            return None
        try:
            parts = tuple(int(part.strip()) for part in name[6:-1].split(","))
        except ValueError:
            return None
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]
