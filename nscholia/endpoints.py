"""
created 2025-12-17
author wf
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from lodstorage.query import Endpoint, QueryManager
from lodstorage.sparql import SPARQL
from snapquery.snapquery_core import NamedQueryManager, Query

from nscholia.useragent import USER_AGENT


class Endpoints:
    """
    endpoints access
    """

    def __init__(self):
        self.nqm = NamedQueryManager.from_samples()
        # Initialize QueryManager with the specific YAML path for dashboard queries
        yaml_path = (
            Path(__file__).parent.parent
            / "nscholia_examples"
            / "dashboard_queries.yaml"
        )
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Query YAML file not found: {yaml_path}")
        self.qm = QueryManager(
            lang="sparql", queriesPath=yaml_path, with_default=False, debug=False
        )

    def get_endpoints(self) -> Dict[str, Any]:
        """
        list all endpoints
        """
        endpoints = self.nqm.endpoints
        return endpoints

    def runQuery(self, query: Query) -> Optional[List[Dict[str, Any]]]:
        """
        Run a SPARQL query and return results as list of dicts

        Args:
            query: Query object to execute

        Returns:
            List of dictionaries containing query results, or None if error
        """
        endpoint = SPARQL(query.endpoint, agent=USER_AGENT)
        if query.params.has_params:
            query.apply_default_params()
        qlod = endpoint.queryAsListOfDicts(
            query.query, param_dict=query.params.params_dict
        )
        return qlod

    def update_state_query_for_endpoint(self, ep: Endpoint) -> Query:
        """
        get the update state query for the given endpoint
        """
        query = None
        query_name = "TripleCount"
        if "wikidata" in ep.name.lower():
            if ep.database == "blazegraph":
                query_name = "WikidataUpdateState"
            elif ep.database == "qlever":
                query_name = "QLeverUpdateState"
        if query_name in self.qm.queriesByName:
            query = self.qm.queriesByName.get(query_name)
            query.endpoint = ep.endpoint
        return query

    def triple_count_query_for_endpoint(self, ep: Endpoint) -> Query:
        """
        get the generic triple count query for the given endpoint - needed
        for endpoints whose update state query returns a timestamp only
        """
        query = self.qm.queriesByName.get("TripleCount")
        if query:
            query.endpoint = ep.endpoint
        return query


@dataclass
class UpdateState:
    """
    the update state of and endpoint
    """

    # status values - the dashboard colors follow these
    OK = "ok"
    QUERY_FAILED = "query failed"
    UNREACHABLE = "unreachable"

    # error markers that mean the endpoint itself could not be talked to -
    # anything else is a query level problem
    UNREACHABLE_MARKERS = [
        "403",
        "404",
        "410",
        "500",
        "502",
        "503",
        "504",
        "forbidden",
        "not found",
        "unauthorized",
        "name or service not known",
        "nodename nor servname",
        "temporary failure in name resolution",
        "connection refused",
        "connection reset",
        "certificate",
        "timed out",
        "timeout",
    ]

    endpoint_name: str
    triples: Optional[int] = None
    timestamp: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    status: str = UNREACHABLE
    checked: Optional[str] = None

    @classmethod
    def classify(cls, error: str) -> str:
        """
        classify an error message as unreachable or query failure

        Args:
            error: the error message

        Returns:
            UNREACHABLE when the endpoint itself did not answer usably,
            QUERY_FAILED when it answered but the query did not work
        """
        msg = (error or "").lower()
        status = cls.QUERY_FAILED
        for marker in cls.UNREACHABLE_MARKERS:
            if marker in msg:
                status = cls.UNREACHABLE
                break
        return status

    @classmethod
    def from_endpoint(cls, em: Endpoints, ep: Endpoint):
        """
        measure the update state of the given endpoint with a real query
        """
        update_state = cls(triples=0, timestamp=ep.data_seeded, endpoint_name=ep.name)
        update_state.checked = datetime.now().isoformat(timespec="seconds")
        try:
            query = em.update_state_query_for_endpoint(ep)
            qlod = em.runQuery(query)
            success = qlod and len(qlod) > 0
            if success:
                update_state.success = True
                update_state.status = cls.OK
                record = qlod[0]
                if "tripleCount" in record:
                    update_state.triples = int(record.get("tripleCount"))
                for var_name in ["timestamp", "updates_complete_until"]:
                    if var_name in record:
                        timestamp = record.get(var_name)
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.isoformat()
                        update_state.timestamp = timestamp
                        break
            else:
                update_state.error = "empty result"
                update_state.status = cls.QUERY_FAILED
        except Exception as ex:
            update_state.error = f"{type(ex).__name__}: {ex}"
            update_state.status = cls.classify(update_state.error)
        if update_state.status == cls.OK and not update_state.triples:
            # the QLever update state query returns a timestamp only - count
            # the triples with a second real call
            try:
                count_query = em.triple_count_query_for_endpoint(ep)
                qlod = em.runQuery(count_query)
                if qlod and "tripleCount" in qlod[0]:
                    update_state.triples = int(qlod[0].get("tripleCount"))
            except Exception as ex:
                update_state.error = f"triple count: {type(ex).__name__}: {ex}"
        return update_state


@dataclass
class UpdateStateCache:
    """
    update states of all endpoints, measured with real queries and
    refreshed at most once per max_age (daily by default)
    """

    max_age_hours: float = 24.0
    max_workers: int = 8
    cache_path: Path = field(
        default_factory=lambda: Path.home() / ".nicescholia" / "update_states.json"
    )
    states: Dict[str, UpdateState] = field(default_factory=dict)
    refreshed: Optional[str] = None

    def __post_init__(self):
        self.load()

    def load(self):
        """
        load the cached states - a missing or broken cache is simply empty
        """
        try:
            if self.cache_path.exists():
                with open(self.cache_path, encoding="utf-8") as cache_file:
                    record = json.load(cache_file)
                self.refreshed = record.get("refreshed")
                self.states = {
                    key: UpdateState(**state)
                    for key, state in record.get("states", {}).items()
                }
        except Exception as ex:
            print(f"update state cache load failed: {ex}")

    def save(self):
        """
        store the cached states
        """
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "refreshed": self.refreshed,
                "states": {key: asdict(state) for key, state in self.states.items()},
            }
            with open(self.cache_path, "w", encoding="utf-8") as cache_file:
                json.dump(record, cache_file, indent=2)
        except Exception as ex:
            print(f"update state cache save failed: {ex}")

    @property
    def is_stale(self) -> bool:
        """
        True when the cache is older than max_age_hours or was never filled
        """
        stale = True
        if self.refreshed:
            try:
                age = datetime.now() - datetime.fromisoformat(self.refreshed)
                stale = age > timedelta(hours=self.max_age_hours)
            except ValueError:
                stale = True
        return stale

    def get(self, key: str) -> Optional[UpdateState]:
        """
        the cached state of the endpoint with the given key
        """
        return self.states.get(key)

    def refresh(self, em: Endpoints, force: bool = False) -> Dict[str, UpdateState]:
        """
        measure all endpoints with real queries unless the cache is fresh

        Args:
            em: the endpoints to measure
            force: measure even when the cache is fresh

        Returns:
            the measured states by endpoint key
        """
        if not force and not self.is_stale:
            return self.states
        endpoints = em.get_endpoints()
        items = list(endpoints.items())

        def measure(item):
            key, ep = item
            return key, UpdateState.from_endpoint(em, ep)

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(items) or 1)) as executor:
            for key, state in executor.map(measure, items):
                self.states[key] = state
        self.refreshed = datetime.now().isoformat(timespec="seconds")
        self.save()
        return self.states
