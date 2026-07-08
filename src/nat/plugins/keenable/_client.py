# SPDX-FileCopyrightText: Copyright (c) 2026, Keenable. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any

import httpx

from nat.plugin_api import SerializableSecretStr
from nat.plugin_api import get_secret_value

# Hardcoded Keenable API base (not configurable — prevents SSRF).
KEENABLE_BASE_URL = "https://api.keenable.ai"

# Attribution tag Keenable segments integration traffic by.
_KEENABLE_TITLE = "NeMo Agent Toolkit"


def resolve_api_key(api_key: SerializableSecretStr | None) -> str:
    """Resolve the Keenable API key from config or the KEENABLE_API_KEY env var.

    Returns an empty string when no key is configured. Keenable is keyless by
    default, so an empty key is valid and selects the public endpoints.
    """
    if api_key:
        value = (get_secret_value(api_key) or "").strip()
        if value:
            return value
    env_value = (os.environ.get("KEENABLE_API_KEY") or "").strip()
    return env_value


class KeenableClient:
    """Minimal async client for the Keenable HTTP API.

    Keyless by default: with no key it calls the public endpoints
    (``/v1/search/public``, ``/v1/fetch/public``, rate-limited); a key switches to
    the authenticated endpoints (``/v1/search``, ``/v1/fetch``) and lifts the cap.
    """

    def __init__(
        self,
        api_key: str = "",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = (api_key or "").strip()
        self._timeout = timeout
        self._transport = transport

    def _headers(self, json_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "nemo-agent-toolkit-keenable",
            "X-Keenable-Title": _KEENABLE_TITLE,
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def search(self, query: str, **filters: Any) -> dict:
        """POST a search. Keyless unless an API key is set."""
        path = "/v1/search" if self._api_key else "/v1/search/public"
        payload: dict[str, Any] = {"query": query, "mode": "pro"}
        payload.update({k: v for k, v in filters.items() if v is not None})
        async with self._client() as client:
            resp = await client.post(
                f"{KEENABLE_BASE_URL}{path}", json=payload, headers=self._headers(True)
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch(self, url: str) -> dict:
        """GET a page as clean markdown. Keyless unless an API key is set."""
        path = "/v1/fetch" if self._api_key else "/v1/fetch/public"
        async with self._client() as client:
            resp = await client.get(
                f"{KEENABLE_BASE_URL}{path}", params={"url": url}, headers=self._headers(False)
            )
            resp.raise_for_status()
            return resp.json()
