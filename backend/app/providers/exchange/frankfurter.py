from __future__ import annotations

import logging
from datetime import date

from app.http import create_client
from app.providers.base import RateObservation
from app.services.catalog import EXCHANGE_SPECS
from app.services.normalize import to_display_value

logger = logging.getLogger(__name__)

SOURCE_LABEL = "Frankfurter (ECB 일별 환율)"


class FrankfurterProvider:
    name = "frankfurter"
    is_mock = False

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_history(self, pair: str, start: date, end: date) -> list[RateObservation]:
        spec = EXCHANGE_SPECS[pair]
        extra = spec.extra
        base = extra["base_currency"]
        quote = extra["quote_currency"]
        url = f"{self.base_url}/{start.isoformat()}..{end.isoformat()}"
        params = {"base": base, "symbols": quote}

        with create_client() as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        rates = payload.get("rates") or {}
        points: list[RateObservation] = []
        for day, quotes in sorted(rates.items()):
            if quote not in quotes:
                continue
            raw = float(quotes[quote])
            display = to_display_value(
                raw,
                display_scale=extra.get("display_scale", 1),
                source_scale=extra.get("source_scale", 1),
            )
            points.append(
                RateObservation(
                    pair=pair,
                    observed_at=date.fromisoformat(day),
                    value=round(display, 4),
                    source=SOURCE_LABEL,
                    is_mock=False,
                )
            )
        logger.info("Fetched %s Frankfurter points for %s", len(points), pair)
        return points
