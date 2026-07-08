# Publishing nemo-agent-toolkit-keenable

Published to PyPI via **Trusted Publishing** (OIDC, no stored tokens), the same
model as the other Keenable Python packages. Publishing is triggered by creating
a GitHub Release; `.github/workflows/publish.yml` builds with `uv` and publishes
via `pypa/gh-action-pypi-publish`.

## One-time setup (PyPI side)

Register a **pending publisher** at <https://pypi.org/manage/account/publishing/>
(or on the project once it exists) with:

| Field | Value |
| --- | --- |
| PyPI Project Name | `nemo-agent-toolkit-keenable` |
| Owner | `keenableai` |
| Repository name | `NeMo-Agent-Toolkit-keenable` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

The workflow's `publish` job runs in the `pypi` GitHub environment; add a
required reviewer there if desired.

## Release

1. Bump `version` in `pyproject.toml`.
2. Tag and create a GitHub Release (e.g. `v0.1.0`). CI builds and publishes.

## Local build / test

```bash
python3.13 -m venv .venv && . .venv/bin/activate   # NeMo requires Python 3.11-3.13
pip install -e ".[test]"
pytest -q            # 8 tests
python -m build      # wheel + sdist
```

## Usage

```yaml
function_groups:
  keenable:
    _type: keenable          # keyless by default; set KEENABLE_API_KEY to lift the cap
    include: [search, fetch]
```

Exposes `keenable__search` and `keenable__fetch`.
