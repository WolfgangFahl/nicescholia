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
| `nscholia/backend.py` | `Backend`/`Backends` — Scholia mirror backend config (`nscholia_examples/backends.yaml`) |
| `nscholia/backend_dashboard.py` | backend live-status dashboard |
| `nscholia/monitor.py` | URL availability checks |
| `nscholia/version.py` | `Version` dataclass — single source of project metadata |
| `nscholia_examples/` | YAML configs: `backends.yaml`, `dashboard_queries.yaml` |
| `tests/` | unittest based tests (`Basetest`/`WebserverTest`) |

## REST API

Registered in `ScholiaWebserver.__init__` via the NiceGUI FastAPI `app`
(snapquery pattern); interactive docs at `/docs`:

- `GET /api/version` — version metadata
- `GET /api/backends` — configured Scholia mirror backends

## Conventions

- Build backend: **hatchling**; version lives in `nscholia/__init__.py` (`__version__`)
- Tests: **unittest** with `basemkit.basetest.Basetest` / `ngwidgets.webserver_test.WebserverTest`; no pytest fixtures, no conftest.py
- Formatting: black (88 cols) + isort via `scripts/blackisort`; no ruff/flake8/mypy
- Docstrings: Google style; module headers with creation date and `@author: wf`
- Type hints on all public signatures; `Optional[X]` not `X | None`
- Named return variables; top-level imports only
- Dependencies: pybasemkit, ngwidgets, snapquery, pyLoDStorage ecosystem — justify any new dependency
