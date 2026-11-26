# SPDX-FileCopyrightText: Copyright (c) 2026, Keenable. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.metadata
import json

import httpx
import pytest

from nat.plugin_api import SerializableSecretStr
from nat.plugins.keenable._client import KeenableClient
from nat.plugins.keenable._client import resolve_api_key
from nat.plugins.keenable.tools import KeenableFetchInput
from nat.plugins.keenable.tools import KeenableSearchInput
from nat.plugins.keenable.tools import KeenableToolsGroupConfig
from nat.plugins.keenable.tools import clean_objective


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
    assert {"site", "published_after", "objective", "max_results"} <= set(fields)
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


async def test_fetch_keyless_posts_to_public_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/fetch/public"
        assert json.loads(request.content) == {"urls": ["https://example.com/a"]}
        assert "X-API-Key" not in request.headers
        return httpx.Response(
            200, json={"results": [{"url": "https://example.com/a", "title": "T", "content": "# T"}]}
        )

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    page = await client.fetch("https://example.com/a")
    assert page["title"] == "T"


async def test_fetch_keyed_posts_to_auth_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/fetch"
        assert request.headers["X-API-Key"] == "keen_test"
        return httpx.Response(200, json={"results": [{"url": "https://example.com/a", "content": "x"}]})

    client = KeenableClient(api_key="keen_test", transport=httpx.MockTransport(handler))
    await client.fetch("https://example.com/a")


async def test_fetch_page_error_raises_http_status_error():
    def handler(request: httpx.Request) -> httpx.Response:
        error = {"status": 404, "message": "page not found"}
        return httpx.Response(200, json={"results": [{"url": "https://example.com/a", "error": error}]})

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError) as exc:
        await client.fetch("https://example.com/a")
    assert exc.value.response.status_code == 404


async def test_search_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "rate limited"})

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.search("q")


def test_clean_objective_trims_and_drops_blank():
    assert clean_objective("  Find the 2026 figure.  ") == "Find the 2026 figure."
    assert clean_objective(None) is None
    assert clean_objective("") is None
    assert clean_objective("   ") is None


async def test_search_sends_objective_only_when_given():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"query": "q", "results": []})

    client = KeenableClient(api_key="", transport=httpx.MockTransport(handler))
    await client.search("q", objective=clean_objective("  why  "))
    await client.search("q", objective=clean_objective("   "))
    assert seen[0]["objective"] == "why"
    assert "objective" not in seen[1]


def test_clean_objective_rejects_over_limit():
    with pytest.raises(ValueError, match="1000"):
        clean_objective("x" * 1001)
    assert len(clean_objective(" " + "x" * 1000 + " ")) == 1000
