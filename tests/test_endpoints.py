"""
Created on 17.12.2025

@author: wf
"""

import os
import traceback
from pathlib import Path

from basemkit.basetest import Basetest
from lodstorage.query import Endpoint, QueryManager

from nscholia.endpoints import Endpoints, UpdateState
from tests.action_stats import ActionStats


class TestUpdateState(Basetest):
    """
    Test update state tracking for SPARQL endpoints
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.em = Endpoints()
        self.endpoints = self.em.get_endpoints()
        yaml_path = (
            Path(__file__).parent.parent
            / "nscholia_examples"
            / "dashboard_queries.yaml"
        )
        self.assertTrue(os.path.exists(yaml_path), yaml_path)
        self.qm = QueryManager(
            lang="sparql", queriesPath=yaml_path, with_default=False, debug=self.debug
        )

    def testDblp(self):
        """
        testDBLP endpoint
        """
        endpoint = Endpoint()
        endpoint.endpoint = "https://sparql.dblp.org/sparql"
        endpoint.url = "https://sparql.dblp.org/sparql"
        endpoint.database = "qlever"
        update_state = UpdateState.from_endpoint(self.em, endpoint)
        debug = self.debug
        debug = True
        if debug:
            print(update_state)

    def testTriplesAndUpdate(self):
        """
        test triples and Updates for both Blazegraph and QLever endpoints
        """
        debug = self.debug
        debug = True

        stats = ActionStats()
        results_by_endpoint = {}

        for ep_name, ep in self.endpoints.items():
            if debug:
                print(f"\nTesting: {ep_name}")
            try:
                update_state = UpdateState.from_endpoint(self.em, ep)
                if debug:
                    print(update_state)
                stats.add(update_state.success)

            except Exception as ex:
                stats.add(False)
                if debug:
                    print(f"❌ Query failed: {ex}")
                    if self.debug:
                        print(traceback.format_exc())

        if debug:
            print(f"\n{stats}")

        # At least one endpoint should work
        self.assertGreater(
            stats.success_count, 0, "At least one endpoint should return results"
        )

        return results_by_endpoint
