from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data"

DEFAULT_NEWS_FEEDS = (
    "https://news.google.com/rss/search?q=%ED%99%98%EC%9C%A8+OR+FOMC+OR+%EC%97%B0%EC%A4%80+OR+%ED%95%9C%EA%B5%AD%EC%9D%80%ED%96%89&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=%EC%9C%84%EC%95%88%ED%99%94+OR+%EC%9B%90%2F%EC%9C%84%EC%95%88+OR+CNY+OR+%EC%9D%B8%EB%AF%BC%EC%9D%80%ED%96%89&hl=ko&gl=KR&ceid=KR:ko",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FX Intelligence Dashboard"
    environment: str = "development"
    database_url: str = f"sqlite:///{DATA_DIR / 'fx.db'}"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    )

    exchange_provider: str = "frankfurter"
    news_provider: str = "rss"
    allow_mock_fallback: bool = True

    frankfurter_base_url: str = "https://api.frankfurter.dev/v1"
    history_start_date: str = "2020-01-01"
    http_timeout_seconds: float = 30.0

    scheduler_enabled: bool = True
    exchange_sync_minutes: int = 360
    news_sync_minutes: int = 60
    forecast_sync_minutes: int = 720
    news_cleanup_hours: int = 24
    news_retention_days: int = 1200
    news_history_months: int = 24
    news_history_min_per_month: int = 2
    news_history_batch_months: int = 8

    admin_api_enabled: bool = True
    auto_ingest_on_startup: bool = True

    news_rss_urls: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def news_feed_list(self) -> list[str]:
        extra = [item.strip() for item in self.news_rss_urls.split(",") if item.strip()]
        return list(DEFAULT_NEWS_FEEDS) + extra

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
