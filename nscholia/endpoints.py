"""
created 2025-12-17
author wf
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lodstorage.query import Endpoint, QueryManager
from lodstorage.sparql import SPARQL
from snapquery.snapquery_core import NamedQueryManager, Query


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
        endpoint = SPARQL(query.endpoint)
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


@dataclass
class UpdateState:
    """
    the update state of and endpoint
    """

    endpoint_name: str
    triples: Optional[int] = None
    timestamp: Optional[str] = None
    success: bool = False
    error: Optional[str] = None

    @classmethod
    def from_endpoint(cls, em: Endpoints, ep: Endpoint):
        update_state = cls(triples=0, timestamp=ep.data_seeded, endpoint_name=ep.name)
        try:
            query = em.update_state_query_for_endpoint(ep)
            qlod = em.runQuery(query)
            success = qlod and len(qlod) > 0
            if success:
                update_state.success = True
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
                update_state.error = "query failed"
        except Exception as ex:
            update_state.error = str(ex)
        return update_state
