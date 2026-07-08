# SPDX-FileCopyrightText: Copyright (c) 2026, Keenable. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.metadata

import httpx
import pytest

from nat.plugin_api import SerializableSecretStr
from nat.plugins.keenable._client import KeenableClient
from nat.plugins.keenable._client import resolve_api_key
from nat.plugins.keenable.tools import KeenableFetchInput
from nat.plugins.keenable.tools import KeenableSearchInput
from nat.plugins.keenable.tools import KeenableToolsGroupConfig


def test_package_entry_point_loads_keenable_plugin():
    dist = importlib.metadata.distribution("nemo-agent-toolkit-keenable")
    plugin_entry_points = {ep.name: ep for ep in dist.entry_points if ep.group == "nat.plugins"}
    assert plugin_entry_points["nat_keenable"].value == "nat.plugins.keenable.register"
    # New third-party packages should not use the compatibility-only nat.components group.
    assert not [ep for ep in dist.entry_points if ep.group == "nat.components"]


def test_config_is_keyless_by_default(monkeypatch):
    monkeypatch.delenv("KEENABLE_API_KEY", raising=False)
    config = KeenableToolsGroupConfig()
    assert resolve_api_key(config.api_key) == ""


def test_resolve_api_key_prefers_config_then_env(monkeypatch):
    monkeypatch.setenv("KEENABLE_API_KEY", "keen_env")
    assert resolve_api_key(SerializableSecretStr("keen_cfg")) == "keen_cfg"
    assert resolve_api_key(SerializableSecretStr("")) == "keen_env"


def test_search_input_schema_fields():
    fields = KeenableSearchInput.model_fields
    assert "query" in fields
    assert {"site", "published_after", "max_results"} <= set(fields)
    assert "url" in KeenableFetchInput.model_fields


async def test_search_keyless_hits_public_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search/public"
        assert "X-API-Key" not in request.headers
        assert request.headers["X-Keenable-Title"] == "NeMo Agent Toolkit"
        return httpx.Response(
            200,
            json={"query": "q", "results": [
                {"title": "A", "url": "https://a", "description": "da"},
                {"title": "B", "url": "https://b", "description": "db"},
            ]},
        )

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    data = await client.search("q")
    assert len(data["results"]) == 2
    assert data["results"][0]["title"] == "A"


async def test_search_keyed_hits_auth_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        assert request.headers["X-API-Key"] == "keen_test"
        return httpx.Response(200, json={"query": "q", "results": []})

    client = KeenableClient(api_key="keen_test", transport=httpx.MockTransport(handler))
    await client.search("q")


async def test_fetch_keyless_hits_public_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/fetch/public"
        assert request.url.params.get("url") == "https://example.com/a"
        return httpx.Response(200, json={"url": "https://example.com/a", "title": "T", "content": "# T"})

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    page = await client.fetch("https://example.com/a")
    assert page["title"] == "T"


async def test_search_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "rate limited"})

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.search("q")
