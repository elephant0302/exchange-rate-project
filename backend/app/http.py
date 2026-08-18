from __future__ import annotations

import httpx

from app.config import get_settings


def create_client(timeout: float | None = None) -> httpx.Client:
    settings = get_settings()
    # trust_env=True honors HTTP_PROXY / HTTPS_PROXY / NO_PROXY.
    return httpx.Client(
        timeout=timeout or settings.http_timeout_seconds,
        follow_redirects=True,
        trust_env=True,
        headers={"User-Agent": "fx-intelligence-dashboard/1.0"},
    )
