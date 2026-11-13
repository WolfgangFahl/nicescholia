# AGENTS.md - nicescholia

## Project Overview

nicescholia is a [NiceGUI](https://nicegui.io) based frontend for
[Scholia](https://scholia.toolforge.org) — scholarly profiles based on Wikidata.
It provides dashboards for SPARQL endpoints (update state / triple counts),
Scholia example queries, and Scholia mirror backends, plus a small REST API.

- **GitHub**: https://github.com/WolfgangFahl/nicescholia
- **Wiki**: https://wiki.bitplan.com/index.php/nicescholia
- **Deployment**: https://nicescholia.wikidata.dbis.rwth-aachen.de
- **Agent**: [Agent/Guido](https://media.bitplan.com/index.php/Agent/Guido) — Python developer agent
- **Agent rules**: [Agent/Guido/BITPlan](https://media.bitplan.com/index.php/Agent/Guido/BITPlan) — canonical BITPlan Python conventions

## Boot

Agents working in the BITPlan context perform the mandatory boot sequence of
[Agents](https://media.bitplan.com/index.php/Agents) on the media wiki (wikipush
wiki id `media`): PLAN-AND-ASK, Document-First, DMAIC histogram, English-only.

## Commands

| Command | Purpose |
|---------|---------|
| `scripts/install` | pip install . |
| `scripts/test` | run the unittest suite (green mode) |
| `scripts/blackisort` | format code with isort + black — always before commit |
| `scripts/doc` | build API documentation |
| `scripts/release` | release to PyPI |
| `checkos -o WolfgangFahl -p nicescholia --local -v -ws /Users/wf/py-workspace` | BITPlan compliance checks |

## Project Structure

| Path | Purpose |
|------|---------|
| `nscholia/webserver.py` | `ScholiaWebserver` / `ScholiaSolution` — NiceGUI pages `/`, `/examples`, `/backends` and REST API |
| `nscholia/cmd.py` | `ScholiaCmd` command line entry point |
| `nscholia/endpoints.py` | SPARQL endpoint access and `UpdateState` |
| `nscholia/endpoint_dashboard.py` | endpoint update-state dashboard (home page) |
| `nscholia/examples_dashboard.py` | Scholia examples dashboard (Google Sheet driven) |
| `nscholia/aspect.py` | `AspectQueries` — named parameterized queries of the Scholia aspects, run on the first working endpoint with the prefix sets of the endpoint |
| `nscholia/aspect_view.py` | `AspectView` — a single view of an aspect shown by the display type of its query |
| `nscholia/backend.py` | `Backend`/`Backends` — Scholia mirror backend config (`nscholia_examples/backends.yaml`) |
| `nscholia/backend_dashboard.py` | backend live-status dashboard |
| `nscholia/monitor.py` | URL availability checks |
| `nscholia/version.py` | `Version` dataclass — single source of project metadata |
| `nscholia_examples/` | YAML configs: `backends.yaml`, `dashboard_queries.yaml`, `aspect_queries.yaml` |
| `tests/` | unittest based tests (`Basetest`/`WebserverTest`) |

## REST API

Registered in `ScholiaWebserver.__init__` via the NiceGUI FastAPI `app`
(snapquery pattern); interactive docs at `/docs`:

- `GET /api/version` — version metadata
- `GET /api/backends` — configured Scholia mirror backends
- `GET /api/<aspect>/<view>/<pid>` — rows of a single view, e.g. `/api/author/list-of-publications/Q80`

## Aspect queries

Scholia is replicated walk by walk, see [#15](https://github.com/WolfgangFahl/nicescholia/issues/15):

- one query issue per walk; the query is taken over once from its Scholia template and from then on owned by nicescholia
- queries live in `nscholia_examples/aspect_queries.yaml` in the pyLoDStorage format, named `<aspect>_<view>` after the Scholia panel, with a `param_list` with defaults and a `<name>-count` companion
- a query carries no PREFIX lines — the prefixes come from the `prefix_sets` of the endpoint
- routes: `/<aspect>/<pid>` aspect page, `/<aspect>/<view>/<pid>` single view, see [#17](https://github.com/WolfgangFahl/nicescholia/issues/17)
- expected results in the tests are bounds and members: they can falsify a walk, not verify it

## Conventions

- Build backend: **hatchling**; version lives in `nscholia/__init__.py` (`__version__`)
- Tests: **unittest** with `basemkit.basetest.Basetest` / `ngwidgets.webserver_test.WebserverTest`; no pytest fixtures, no conftest.py
- Formatting: black (88 cols) + isort via `scripts/blackisort`; no ruff/flake8/mypy
- Docstrings: Google style; module headers with creation date and `@author: wf`
- Type hints on all public signatures; `Optional[X]` not `X | None`
- Named return variables; top-level imports only
- Dependencies: pybasemkit, ngwidgets, snapquery, pyLoDStorage ecosystem — justify any new dependency
