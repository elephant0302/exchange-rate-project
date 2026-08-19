from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.providers.base import ForecastPoint, ForecastResult

logger = logging.getLogger(__name__)

# Meese-Rogoff (1983) and Rossi (2013): short-horizon FX is judged against a random walk.
MIN_OBSERVATIONS = 90
CONFIDENCE = 0.95
Z_95 = 1.96
FOLD_SIZE = 7
FOLDS = 3
AR_MAX_LAG = 3
GARCH_GRID_ALPHA = (0.03, 0.06, 0.10, 0.15)
GARCH_GRID_BETA = (0.80, 0.85, 0.90, 0.94)


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


def log_returns(series: np.ndarray) -> np.ndarray:
    return np.diff(np.log(np.clip(series, 1e-6, None)))


def return_volatility(series: np.ndarray, window: int = 63) -> float:
    returns = log_returns(series)
    if len(returns) < 2:
        return 0.01
    sample = returns[-min(window, len(returns)) :]
    sigma = float(np.std(sample, ddof=1)) if len(sample) > 1 else float(np.std(sample))
    return max(sigma, 1e-4)


def _rw_path(last: float, horizon: int) -> np.ndarray:
    """Random walk without drift — the Meese-Rogoff benchmark."""
    return np.full(horizon, last)


def _compound(last: float, returns: np.ndarray) -> np.ndarray:
    return last * np.exp(np.cumsum(returns))


def _ar_path(series: np.ndarray, horizon: int) -> np.ndarray | None:
    """AR(p) on log-returns, lag chosen by AIC. Standard short-horizon time-series model."""
    returns = log_returns(series)
    if len(returns) < 20:
        return None
    best_fit = None
    best_aic = float("inf")
    for lag in range(1, AR_MAX_LAG + 1):
        try:
            fitted = AutoReg(returns, lags=lag, old_names=False).fit()
            aic = float(fitted.aic)
            if np.isfinite(aic) and aic < best_aic:
                best_aic = aic
                best_fit = fitted
        except Exception as exc:
            logger.info("AR(%s) skipped: %s", lag, exc)
    if best_fit is None:
        return None
    try:
        predicted = np.asarray(best_fit.forecast(steps=horizon), dtype=float)
    except Exception as exc:
        logger.info("AR forecast failed: %s", exc)
        return None
    if len(predicted) != horizon or np.any(~np.isfinite(predicted)):
        return None
    return _compound(float(series[-1]), predicted)


def _holt_path(series: np.ndarray, horizon: int) -> np.ndarray | None:
    """Holt linear exponential smoothing (Hyndman ETS-style, no seasonality)."""
    if len(series) < 20:
        return None
    try:
        fitted = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        ).fit(optimized=True)
        predicted = np.asarray(fitted.forecast(horizon), dtype=float)
    except Exception as exc:
        logger.info("Holt forecast failed: %s", exc)
        return None
    if len(predicted) != horizon or np.any(~np.isfinite(predicted)):
        return None
    return predicted


def _align_factor(
    dates: list[date],
    factor_dates: list[date],
    factor_values: list[float],
) -> np.ndarray:
    lookup = {day: value for day, value in zip(factor_dates, factor_values)}
    aligned = np.full(len(dates), np.nan, dtype=float)
    last = np.nan
    for index, day in enumerate(dates):
        if day in lookup:
            last = lookup[day]
        aligned[index] = last
    return aligned


def _dollar_factor_path(
    series: np.ndarray,
    factor: np.ndarray,
    horizon: int,
) -> np.ndarray | None:
    """Lagged dollar factor: r_t = a + b r_USD,t-1. Cross-rate lead-lag used when USD is available."""
    if len(series) != len(factor) or len(series) < 40:
        return None
    pair_r = log_returns(series)
    usd_r = log_returns(factor)
    y = pair_r[1:]
    x = usd_r[:-1]
    mask = np.isfinite(y) & np.isfinite(x)
    if int(mask.sum()) < 30:
        return None
    design = np.column_stack([np.ones(int(mask.sum())), x[mask]])
    try:
        coef, *_ = np.linalg.lstsq(design, y[mask], rcond=None)
    except np.linalg.LinAlgError:
        return None
    intercept, beta = float(coef[0]), float(coef[1])
    last_usd = usd_r[np.isfinite(usd_r)]
    if len(last_usd) == 0:
        return None
    returns = np.full(horizon, intercept)
    returns[0] = intercept + beta * float(last_usd[-1])
    return _compound(float(series[-1]), returns)


def _fit_garch11(returns: np.ndarray) -> tuple[float, float, float, float, float] | None:
    """Variance-targeting GARCH(1,1) by Gaussian likelihood grid. Used for KRW vol in the literature."""
    if len(returns) < 30:
        return None
    var = float(np.var(returns))
    if var <= 0:
        return None
    best: tuple[float, float, float, float, float] | None = None
    best_ll = -float("inf")
    for alpha in GARCH_GRID_ALPHA:
        for beta in GARCH_GRID_BETA:
            if alpha + beta >= 0.995:
                continue
            omega = (1.0 - alpha - beta) * var
            sigma2 = var
            loglik = 0.0
            last_eps2 = float(returns[0] ** 2)
            for value in returns[1:]:
                sigma2 = omega + alpha * last_eps2 + beta * sigma2
                sigma2 = max(sigma2, 1e-12)
                loglik += -0.5 * (np.log(sigma2) + (value**2) / sigma2)
                last_eps2 = float(value**2)
            if loglik > best_ll:
                best_ll = loglik
                best = (omega, alpha, beta, sigma2, last_eps2)
    return best


def _garch_cum_vol(returns: np.ndarray, horizon: int) -> np.ndarray:
    fitted = _fit_garch11(returns)
    if fitted is None:
        sigma = max(float(np.std(returns, ddof=1) if len(returns) > 1 else 0.01), 1e-4)
        return sigma * np.sqrt(np.arange(1, horizon + 1))
    omega, alpha, beta, last_sigma2, last_eps2 = fitted
    path = np.empty(horizon)
    sigma2 = omega + alpha * last_eps2 + beta * last_sigma2
    path[0] = max(sigma2, 1e-12)
    persist = alpha + beta
    for step in range(1, horizon):
        path[step] = max(omega + persist * path[step - 1], 1e-12)
    return np.sqrt(np.cumsum(path))


def _interval(center: np.ndarray, last: float, cum_vol: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    width = last * Z_95 * cum_vol
    lower = np.maximum(center - width, 0.01)
    upper = center + width
    return lower, upper


def _validation_windows(length: int) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for fold in range(FOLDS):
        valid_end = length - (FOLDS - 1 - fold) * FOLD_SIZE
        valid_start = valid_end - FOLD_SIZE
        if valid_start < MIN_OBSERVATIONS // 2:
            continue
        windows.append((valid_start, valid_end))
    return windows


def _candidate_paths(
    series: np.ndarray,
    horizon: int,
    factor: np.ndarray | None,
) -> dict[str, np.ndarray]:
    paths: dict[str, np.ndarray] = {"RW": _rw_path(float(series[-1]), horizon)}
    ar_path = _ar_path(series, horizon)
    if ar_path is not None:
        paths["AR"] = ar_path
    holt_path = _holt_path(series, horizon)
    if holt_path is not None:
        paths["Holt"] = holt_path
    if factor is not None:
        dollar_path = _dollar_factor_path(series, factor, horizon)
        if dollar_path is not None:
            paths["DollarFactor"] = dollar_path
    return paths


def combination_weights(scores: list[ModelScore]) -> dict[str, float]:
    """Bates-Granger inverse-MAE weights. Combination is the usual robust alternative to picking one model."""
    usable = [item for item in scores if item.name != "Combination" and item.mae > 0]
    if not usable:
        return {"RW": 1.0}
    raw = {item.name: 1.0 / item.mae for item in usable}
    total = sum(raw.values())
    return {name: weight / total for name, weight in raw.items()}


def _combine(paths: dict[str, np.ndarray], weights: dict[str, float], horizon: int) -> np.ndarray:
    combined = np.zeros(horizon)
    total = 0.0
    for name, weight in weights.items():
        path = paths.get(name)
        if path is None or len(path) != horizon:
            continue
        combined += weight * path
        total += weight
    if total <= 0:
        return next(iter(paths.values()))
    return combined / total


class StatisticalForecastProvider:
    name = "statistical"

    def generate(
        self,
        pair: str,
        dates: list[date],
        values: list[float],
        horizon: int = 30,
        factor_dates: list[date] | None = None,
        factor_values: list[float] | None = None,
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
        factor = None
        if factor_dates and factor_values and pair != "USD_KRW":
            factor = _align_factor(dates, factor_dates, factor_values)

        scores, residual, fold_paths = self._score_candidates(series, factor)
        if not scores:
            return ForecastResult(
                available=False,
                pair=pair,
                points=[],
                unavailable_reason="검증 구간을 만들 수 없어 예측을 생성하지 않았습니다.",
            )

        weights = combination_weights(scores)
        combo_actual: list[np.ndarray] = []
        combo_pred: list[np.ndarray] = []
        for actual, paths in fold_paths:
            predicted = _combine(paths, weights, len(actual))
            combo_actual.append(actual)
            combo_pred.append(predicted)
        combo_score = ModelScore(
            "Combination",
            mae(np.concatenate(combo_actual), np.concatenate(combo_pred)),
            rmse(np.concatenate(combo_actual), np.concatenate(combo_pred)),
        )
        scores.append(combo_score)

        try:
            paths = _candidate_paths(series, horizon, factor)
            center = _combine(paths, weights, horizon)
            vol = _garch_cum_vol(log_returns(series), horizon)
            last = float(series[-1])
            lower, upper = _interval(center, last, vol)
            holdout_width = Z_95 * residual * np.sqrt(np.arange(1, horizon + 1))
            lower = np.minimum(lower, center - holdout_width)
            upper = np.maximum(upper, center + holdout_width)
            lower = np.maximum(lower, 0.01)
        except Exception as exc:
            logger.exception("Forecast generation failed for %s", pair)
            return ForecastResult(
                available=False,
                pair=pair,
                points=[],
                unavailable_reason=f"모델 생성에 실패했습니다: {exc.__class__.__name__}",
            )

        members = "+".join(name for name in ("RW", "AR", "Holt", "DollarFactor") if name in weights)
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
            model_name=f"Combination({members})+GARCH(1,1)",
            confidence_level=CONFIDENCE,
            trained_from=dates[0],
            trained_to=dates[-1],
            mae=round(combo_score.mae, 4),
            rmse=round(combo_score.rmse, 4),
            comparisons={
                score.name: {"mae": round(score.mae, 4), "rmse": round(score.rmse, 4)}
                for score in scores
            },
        )

    def _score_candidates(
        self,
        series: np.ndarray,
        factor: np.ndarray | None,
    ) -> tuple[list[ModelScore], float, list[tuple[np.ndarray, dict[str, np.ndarray]]]]:
        windows = _validation_windows(len(series))
        collected: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
        fold_paths: list[tuple[np.ndarray, dict[str, np.ndarray]]] = []
        for start, end in windows:
            train = series[:start]
            valid = series[start:end]
            train_factor = factor[:start] if factor is not None else None
            paths = _candidate_paths(train, len(valid), train_factor)
            fold_paths.append((valid, paths))
            for name, predicted in paths.items():
                collected.setdefault(name, []).append((predicted, valid))

        scores: list[ModelScore] = []
        residuals: list[float] = []
        for name, pairs in collected.items():
            actual = np.concatenate([valid for _, valid in pairs])
            predicted = np.concatenate([pred for pred, _ in pairs])
            scores.append(ModelScore(name, mae(actual, predicted), rmse(actual, predicted)))
            residuals.append(float(np.std(actual - predicted, ddof=1)) if len(actual) > 1 else 1.0)
        residual = max(residuals) if residuals else 1.0
        return scores, residual, fold_paths
