"""
Created on 17.12.2025

@author: wf
"""
import os
from pathlib import Path
import traceback

from basemkit.basetest import Basetest
from lodstorage.query import QueryManager
from nscholia.endpoints import Endpoints

from tests.action_stats import ActionStats


class TestUpdateState(Basetest):
    """
    Test update state tracking for SPARQL endpoints
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.em=Endpoints()
        self.endpoints = self.em.get_endpoints()
        yaml_path = Path(__file__).parent.parent / "nscholia_examples" / "dashboard_queries.yaml"
        self.assertTrue(os.path.exists(yaml_path),yaml_path)
        self.qm = QueryManager(
            lang="sparql", queriesPath=yaml_path, with_default=False, debug=self.debug
        )

    def testTriplesAndUpdate(self):
        """
        test triples and Updates for both Blazegraph and QLever endpoints
        """
        debug = self.debug
        debug = True

        stats = ActionStats()
        results_by_endpoint = {}

        for ep_name, ep in self.endpoints.items():
            # Select query based on database type
            query_name = None

            if ep.database == 'blazegraph' and 'wikidata' in ep_name.lower():
                query_name = 'WikidataUpdateState'
            elif ep.database == 'qlever':
                query_name = 'QLeverUpdateState'  # or whatever the actual query name is
            else:
                if debug:
                    print(f"Skipping {ep_name} - no suitable query")
                continue

            if query_name not in self.qm.queriesByName:
                if debug:
                    print(f"Query '{query_name}' not found, skipping {ep_name}")
                continue

            query = self.qm.queriesByName[query_name]
            if debug:
                print(f"\nTesting: {ep_name}")

            try:
                query.endpoint=ep.endpoint
                qlod = self.em.runQuery(query)
                success = qlod and len(qlod) > 0

                if success:
                    result = qlod[0]
                    results_by_endpoint[ep_name] = result

                    if debug:
                        print(stats.state(
                            f"Got data for {ep_name}",
                            f"No data for {ep_name}"
                        ))
                        for key, value in result.items():
                            print(f"  {key}: {value}")

                stats.add(success)

            except Exception as ex:
                stats.add(False)
                if debug:
                    print(f"❌ Query failed: {ex}")
                    if self.debug:
                        print(traceback.format_exc())

        if debug:
            print(f"\n{stats}")

        # At least one endpoint should work
        self.assertGreater(stats.success_count, 0, "At least one endpoint should return results")

        return results_by_endpoint