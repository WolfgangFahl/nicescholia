from typing import Optional, List, Dict, Any
from lodstorage.sparql import SPARQL
from snapquery.snapquery_core import NamedQueryManager, Query


class Endpoints:
    """
    endpoints access
    """
    def __init__(self):
        self.nqm = NamedQueryManager.from_samples()

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

