# SPDX-FileCopyrightText: Copyright (c) 2026, Keenable. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import AsyncIterator

from pydantic import BaseModel
from pydantic import Field

from nat.plugin_api import Builder
from nat.plugin_api import FunctionGroup
from nat.plugin_api import FunctionGroupBaseConfig
from nat.plugin_api import SerializableSecretStr
from nat.plugin_api import register_function_group

from ._client import KeenableClient
from ._client import resolve_api_key

logger = logging.getLogger(__name__)


class KeenableSearchInput(BaseModel):
    """Input for the Keenable search tool."""

    query: str = Field(description="The search query.")
    site: str | None = Field(
        default=None, description="Restrict results to a single domain, e.g. 'techcrunch.com'."
    )
    published_after: str | None = Field(
        default=None, description="Only pages published on or after this date (YYYY-MM-DD)."
    )
    published_before: str | None = Field(
        default=None, description="Only pages published on or before this date (YYYY-MM-DD)."
    )
    acquired_after: str | None = Field(
        default=None, description="Only pages indexed on or after this date (YYYY-MM-DD)."
    )
    acquired_before: str | None = Field(
        default=None, description="Only pages indexed on or before this date (YYYY-MM-DD)."
    )
    max_results: int | None = Field(
        default=None, ge=1, le=20, description="Maximum number of results to return (1-20)."
    )


class KeenableFetchInput(BaseModel):
    """Input for the Keenable fetch tool."""

    url: str = Field(description="The URL of the page to fetch and extract as markdown.")


class KeenableToolsGroupConfig(FunctionGroupBaseConfig, name="keenable"):
    """Keenable tools group: web search and page fetch.

    Keyless by default. The tools call Keenable's public endpoints with no key
    (rate-limited); set an API key (or the KEENABLE_API_KEY env var) to lift the cap.
    """

    api_key: SerializableSecretStr = Field(
        default_factory=lambda: SerializableSecretStr(""),
        description="Optional Keenable API key. Keyless by default; falls back to the "
        "KEENABLE_API_KEY env var. A key lifts the hourly rate limit.",
    )
    timeout_seconds: float = Field(
        default=30.0, gt=0, description="HTTP timeout for Keenable requests, in seconds."
    )


_SEARCH_DESCRIPTION = (
    "Search the web with Keenable for up-to-date information. Returns ranked results "
    "(title, url, description, and publication/index dates). Supports filtering by site "
    "and date. Keyless by default."
)
_FETCH_DESCRIPTION = (
    "Fetch a web page via Keenable and return its main content as clean markdown, along "
    "with title, description, author, and publication date. Use after search to read a page."
)


@register_function_group(config_type=KeenableToolsGroupConfig)
async def keenable_tools(
    config: KeenableToolsGroupConfig, _builder: Builder
) -> AsyncIterator[FunctionGroup]:
    """Register the `keenable` function group (search, fetch)."""
    client = KeenableClient(
        api_key=resolve_api_key(config.api_key), timeout=config.timeout_seconds
    )

    async def _search(value: KeenableSearchInput) -> dict:
        data = await client.search(
            value.query,
            site=value.site,
            published_after=value.published_after,
            published_before=value.published_before,
            acquired_after=value.acquired_after,
            acquired_before=value.acquired_before,
        )
        results = data.get("results", []) if isinstance(data, dict) else []
        if value.max_results is not None:
            results = results[: value.max_results]
        return {"query": data.get("query", value.query) if isinstance(data, dict) else value.query,
                "results": results}

    async def _fetch(value: KeenableFetchInput) -> dict:
        return await client.fetch(value.url)

    group = FunctionGroup(config=config)
    group.add_function(
        "search", _search, input_schema=KeenableSearchInput, description=_SEARCH_DESCRIPTION
    )
    group.add_function(
        "fetch", _fetch, input_schema=KeenableFetchInput, description=_FETCH_DESCRIPTION
    )

    yield group
