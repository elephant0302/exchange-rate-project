from app.config import Settings
from app.providers.base import ExchangeRateProvider
from app.providers.exchange.frankfurter import FrankfurterProvider
from app.providers.exchange.mock import MockExchangeProvider


def build_exchange_provider(settings: Settings) -> ExchangeRateProvider:
    if settings.exchange_provider.lower() == "mock":
        return MockExchangeProvider()
    return FrankfurterProvider(base_url=settings.frankfurter_base_url)
