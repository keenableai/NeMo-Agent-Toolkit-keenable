# nemo-agent-toolkit-keenable

[Keenable](https://keenable.ai) web search and page-fetch tools for the [NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/), packaged as a provider-owned third-party plugin.

**Keyless by default.** The tools call Keenable's public endpoints with no API key (rate-limited). An optional `KEENABLE_API_KEY` lifts the hourly cap; it is never a prerequisite.

## Installation

```bash
pip install nemo-agent-toolkit-keenable
```

Installing it in the same environment as `nvidia-nat-core` registers the `keenable` function group via a Python entry point.

## Usage

Add the function group to your workflow config and expose the tools you need:

```yaml
function_groups:
  keenable:
    _type: keenable
    # api_key: "keen_..."   # optional; keyless by default (or set KEENABLE_API_KEY)
    include: [search, fetch]
```

This exposes the tools `keenable__search` and `keenable__fetch`.

- **`keenable__search`**: web search. Args: `query` (required), optional `site`, `published_after` / `published_before`, `acquired_after` / `acquired_before` (YYYY-MM-DD), `max_results` (1-20). Returns `{ query, results: [{ title, url, description, published_at, acquired_at }] }`.
- **`keenable__fetch`**: fetch a URL as clean markdown. Args: `url`. Returns `{ url, title, content, description, author, published_at }`.

## Configuration

| Field | Default | Description |
| --- | --- | --- |
| `api_key` | (empty) | Optional Keenable API key. Keyless by default; falls back to `KEENABLE_API_KEY`. A key lifts the rate limit. |
| `timeout_seconds` | `30.0` | HTTP timeout for Keenable requests. |

Get a key at [keenable.ai/console](https://keenable.ai/console).

## License

Apache-2.0
