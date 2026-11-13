"""
Created on 2026-11-13

@author: wf

Named parameterized queries of the Scholia aspects
see https://github.com/WolfgangFahl/nicescholia/issues/15
"""

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lodstorage.prefix_config import PrefixConfigs
from lodstorage.query import Endpoint, Query, QueryManager
from lodstorage.sparql import SPARQL

from nscholia.endpoints import Endpoints
from nscholia.useragent import USER_AGENT


@dataclass
class AspectResult:
    """
    the result of running the query of a single view of an aspect
    """

    aspect: str
    view: str
    params: Dict[str, Any]
    default_view: str = "Table"
    endpoint_name: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)


class AspectQueries:
    """
    the named parameterized queries of the aspects

    a query is named <aspect>_<view> after the Scholia panel it replicates
    and is run on the first working endpoint
    """

    # Wikidata endpoints to try in this order
    ENDPOINT_NAMES: List[str] = ["wikidata-qlever-dbis", "wikidata-dbis"]
    COUNT_SUFFIX: str = "-count"
    # allowed parameter values - anything else never reaches a query
    PID_PATTERN = re.compile(r"^[QPL][0-9]+$")
    DEFAULT_VIEW_PATTERN = re.compile(r"^\s*#defaultView:(\w+)", re.MULTILINE)

    def __init__(self, endpoints: Optional[Endpoints] = None):
        """
        constructor

        Args:
            endpoints: the endpoints to use - created if not given
        """
        self.endpoints = endpoints if endpoints else Endpoints()
        yaml_path = (
            Path(__file__).parent.parent / "nscholia_examples" / "aspect_queries.yaml"
        )
        if not yaml_path.exists():
            raise FileNotFoundError(f"Query YAML file not found: {yaml_path}")
        self.qm = QueryManager(
            lang="sparql", queriesPath=str(yaml_path), with_default=False, debug=False
        )
        self.prefix_configs = PrefixConfigs.get_instance()

    @classmethod
    def query_name(cls, aspect: str, view: str) -> str:
        """
        get the name of the query for the given aspect and view
        """
        name = f"{aspect}_{view}"
        return name

    def views(self) -> Dict[str, List[str]]:
        """
        get the views per aspect derived from the query names

        Returns:
            mapping of aspect to the list of its view names
        """
        views: Dict[str, List[str]] = {}
        for name in self.qm.queriesByName:
            if name.endswith(self.COUNT_SUFFIX) or "_" not in name:
                continue
            aspect, view = name.split("_", 1)
            views.setdefault(aspect, []).append(view)
        return views

    def get_query(self, name: str) -> Query:
        """
        get a copy of the query with the given name

        Args:
            name: the name of the query

        Raises:
            KeyError: if there is no such query
        """
        if name not in self.qm.queriesByName:
            raise KeyError(f"unknown query {name}")
        query = copy.deepcopy(self.qm.queriesByName[name])
        return query

    def default_view(self, query: Query) -> str:
        """
        get the display type of the query from its #defaultView line
        """
        default_view = "Table"
        match = self.DEFAULT_VIEW_PATTERN.search(query.query)
        if match:
            default_view = match.group(1)
        return default_view

    def check_params(self, query: Query, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        merge the given parameters with the defaults and check their values

        Args:
            query: the query with its param_list
            params: the given parameter values

        Raises:
            ValueError: if a parameter is unknown or its value is not allowed
        """
        checked: Dict[str, Any] = {}
        param_list = query.param_list or []
        known = {param.name: param for param in param_list}
        for name in params:
            if name not in known:
                raise ValueError(f"unknown parameter {name}")
        for name, param in known.items():
            value = params.get(name)
            if value is None:
                value = param.default_value
            if param.type == "int":
                value = int(value)
                if value < 1:
                    raise ValueError(f"{name} must be positive")
            elif not self.PID_PATTERN.match(str(value)):
                raise ValueError(f"invalid value for {name}")
            checked[name] = value
        return checked

    def run_query(
        self, query: Query, endpoint: Endpoint, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        run the given query with the prefixes of the given endpoint

        Args:
            query: a copy of the query to run
            endpoint: the endpoint to run it on
            params: the checked parameter values
        """
        query.endpoint = endpoint.endpoint
        query.add_endpoint_prefixes(endpoint, self.prefix_configs)
        sparql = SPARQL(endpoint.endpoint, agent=USER_AGENT)
        lod = sparql.queryAsListOfDicts(query.query, param_dict=params)
        return lod

    def run(
        self,
        aspect: str,
        view: str,
        params: Optional[Dict[str, Any]] = None,
        endpoint_name: Optional[str] = None,
        count: bool = False,
    ) -> AspectResult:
        """
        run the query of the given view on the first working endpoint

        Args:
            aspect: the aspect e.g. author
            view: the view e.g. list-of-publications
            params: the parameter values - defaults apply for missing ones
            endpoint_name: the endpoint to use instead of the default order
            count: if True run the count companion of the query

        Returns:
            the result with rows, columns and the endpoint that answered;
            errors per endpoint that did not answer
        """
        name = self.query_name(aspect, view)
        if count:
            name = f"{name}{self.COUNT_SUFFIX}"
        query = self.get_query(name)
        checked = self.check_params(query, params or {})
        result = AspectResult(
            aspect=aspect,
            view=view,
            params=checked,
            default_view=self.default_view(query),
        )
        endpoint_names = [endpoint_name] if endpoint_name else self.ENDPOINT_NAMES
        available = self.endpoints.get_endpoints()
        for ep_name in endpoint_names:
            endpoint = available.get(ep_name)
            if endpoint is None:
                result.errors[ep_name] = "unknown endpoint"
                continue
            try:
                rows = self.run_query(copy.deepcopy(query), endpoint, checked)
            except Exception as ex:
                result.errors[ep_name] = str(ex)
                continue
            result.endpoint_name = ep_name
            result.rows = rows
            result.columns = self.columns_of(query, rows)
            break
        return result

    @classmethod
    def select_columns(cls, sparql: str) -> List[str]:
        """
        get the result columns from the outermost SELECT clause of a query

        Args:
            sparql: the query text

        Returns:
            the variable names in the order of the SELECT clause - empty
            if the clause can not be read e.g. for SELECT *
        """
        columns: List[str] = []
        match = re.search(
            r"\bSELECT\b(.*?)\bWHERE\b", sparql, re.DOTALL | re.IGNORECASE
        )
        clause = match.group(1) if match else ""
        depth = 0
        for token in re.finditer(r"\(|\)|AS\s+\?(\w+)\s*\)|\?(\w+)", clause):
            text = token.group(0)
            if text == "(":
                depth += 1
            elif text == ")":
                depth -= 1
            elif token.group(1):
                columns.append(token.group(1))
                depth -= 1
            elif depth == 0:
                columns.append(token.group(2))
        return columns

    def columns_of(self, query: Query, rows: List[Dict[str, Any]]) -> List[str]:
        """
        get the columns of a result: the SELECT clause order first, then
        any further column of the rows - the first row alone may miss a
        column that is unbound there
        """
        columns = self.select_columns(query.query)
        for row in rows:
            for column in row:
                if column not in columns:
                    columns.append(column)
        return columns
