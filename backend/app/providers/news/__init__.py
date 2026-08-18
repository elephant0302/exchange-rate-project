from app.config import Settings
from app.providers.base import NewsProvider
from app.providers.news.composite import CompositeNewsProvider
from app.providers.news.mock import MockNewsProvider


def build_news_provider(settings: Settings) -> NewsProvider:
    if settings.news_provider.lower() == "mock":
        return MockNewsProvider()
    return CompositeNewsProvider(feed_urls=settings.news_feed_list)
