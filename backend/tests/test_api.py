from datetime import date, datetime, timedelta, timezone

from app.models import Event, Forecast, Observation
from app.services.catalog import get_indicator
from app.services.ingest import _save_observations
from app.providers.base import RateObservation


def _seed_rates(db, pair: str = "USD_KRW", n: int = 5) -> None:
    indicator = get_indicator(db, pair)
    assert indicator is not None
    start = date(2026, 8, 10)
    points = [
        RateObservation(
            pair=pair,
            observed_at=start + timedelta(days=index),
            value=1400 + index,
            source="test",
            is_mock=True,
        )
        for index in range(n)
    ]
    _save_observations(db, indicator.id, points)


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "providers" in body


def test_indicators(client) -> None:
    response = client.get("/api/indicators")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["data"]}
    assert codes == {"USD_KRW", "EUR_KRW", "JPY_KRW", "CNY_KRW"}
    assert "meta" in response.json()


def test_latest_and_history_schema(client, db) -> None:
    _seed_rates(db)
    latest = client.get("/api/exchange-rates/latest?pair=USD_KRW&period=1M")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["data"]["pair"] == "USD_KRW"
    assert payload["data"]["value"] == 1404
    assert payload["meta"]["unit_label"] == "1달러당 원화"
    assert payload["meta"]["is_mock"] is True

    history = client.get("/api/exchange-rates/history?pair=USD_KRW&period=1M")
    assert history.status_code == 200
    assert len(history.json()["data"]["points"]) == 5


def test_invalid_pair_and_period(client) -> None:
    assert client.get("/api/exchange-rates/latest?pair=GBP_KRW").status_code == 422
    assert client.get("/api/exchange-rates/history?pair=USD_KRW&period=2Y").status_code == 422


def test_news_schema_and_mock_flag(client, db) -> None:
    indicator = get_indicator(db, "USD_KRW")
    db.add(
        Event(
            indicator_id=indicator.id,
            title="[Mock] sample",
            url="https://example.com/news-1",
            normalized_url="https://example.com/news-1",
            source="test",
            published_at=datetime.now(timezone.utc),
            direction="neutral",
            importance="low",
            summary="sample",
            keywords="연준",
            is_mock=True,
        )
    )
    db.commit()
    response = client.get("/api/news?pair=USD_KRW&limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["url"].startswith("https://")
    assert body["data"][0]["is_mock"] is True
    assert body["meta"]["is_mock"] is True


def test_forecast_unavailable_without_enough_data(client, db) -> None:
    _seed_rates(db, n=10)
    response = client.get("/api/forecasts?pair=USD_KRW&horizon=30")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["available"] is False
    assert body["data"]["unavailable_reason"]
    assert body["data"]["points"] == []


def test_forecast_available_schema(client, db) -> None:
    indicator = get_indicator(db, "USD_KRW")
    created = datetime.now(timezone.utc)
    db.add(
        Forecast(
            indicator_id=indicator.id,
            target_at=date(2026, 8, 19),
            predicted_value=1410.0,
            lower_bound=1390.0,
            upper_bound=1430.0,
            confidence_level=0.95,
            model_name="Naive",
            trained_from=date(2025, 1, 2),
            trained_to=date(2026, 8, 17),
            mae=4.2,
            rmse=5.1,
            horizon_days=30,
            is_mock=True,
            created_at=created,
        )
    )
    db.commit()
    response = client.get("/api/forecasts?pair=USD_KRW&horizon=7")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["available"] is True
    assert body["data"]["model_name"] == "Naive"
    assert body["data"]["mae"] == 4.2
    assert body["data"]["points"][0]["lower_bound"] <= body["data"]["points"][0]["upper_bound"]


def test_admin_refresh_uses_mock_provider(client) -> None:
    response = client.post("/api/admin/refresh")
    assert response.status_code == 200
    body = response.json()
    assert "exchange" in body
    assert "news" in body
    latest = client.get("/api/exchange-rates/latest?pair=JPY_KRW")
    assert latest.status_code == 200
    assert latest.json()["meta"]["unit_label"] == "100엔당 원화"
    assert latest.json()["data"]["value"] is not None
    cny = client.get("/api/exchange-rates/latest?pair=CNY_KRW")
    assert cny.status_code == 200
    assert cny.json()["meta"]["unit_label"] == "1위안당 원화"
    assert cny.json()["data"]["value"] is not None
