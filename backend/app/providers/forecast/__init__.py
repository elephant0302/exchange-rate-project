from app.providers.forecast.statistical import StatisticalForecastProvider


def build_forecast_provider() -> StatisticalForecastProvider:
    return StatisticalForecastProvider()
