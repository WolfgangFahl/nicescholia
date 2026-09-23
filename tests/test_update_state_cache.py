"""
Created on 2026-09-23

@author: wf
"""

import tempfile
import urllib.error
from pathlib import Path

from basemkit.basetest import Basetest

from nscholia.endpoints import Endpoints, UpdateState, UpdateStateCache
from nscholia.monitor import Monitor
from nscholia.useragent import USER_AGENT


class TestUpdateStateCache(Basetest):
    """
    test the user agent, the status classification and the daily cache
    """

    def testUserAgent(self):
        """
        the SPARQL calls and the monitor must send the same Wikimedia
        policy compliant User-Agent
        """
        debug = self.debug
        if debug:
            print(USER_AGENT)
        self.assertTrue(USER_AGENT.startswith("nicescholia/"))
        self.assertIn("github.com", USER_AGENT)
        self.assertEqual(USER_AGENT, Monitor.DEFAULT_USER_AGENT)

    def testQLeverTripleCount(self):
        """
        the triple count of a QLever endpoint comes from its stats call
        """
        em = Endpoints()
        for name in ["wikidata-qlever", "wikidata-qlever-dbis"]:
            ep = em.get_endpoints().get(name)
            self.assertIsNotNone(ep, name)
            try:
                triple_count = em.qlever_triple_count(ep)
            except urllib.error.HTTPError as ex:
                if ex.code == 429:
                    self.skipTest(f"{name} rate limits this host: {ex}")
                raise
            if self.debug:
                print(f"{name}: {triple_count:,}")
            self.assertGreater(triple_count, 10_000_000_000, name)

    def testClassify(self):
        """
        an endpoint that does not answer usably is unreachable, anything
        else is a query level failure
        """
        cases = {
            "HTTPError: HTTP Error 403: Forbidden": UpdateState.UNREACHABLE,
            "URLError: <urlopen error [Errno 8] nodename nor servname": UpdateState.UNREACHABLE,
            "TimeoutError: The read operation timed out": UpdateState.UNREACHABLE,
            "QueryBadFormed: malformed query": UpdateState.QUERY_FAILED,
            "empty result": UpdateState.QUERY_FAILED,
        }
        for error, expected in cases.items():
            self.assertEqual(expected, UpdateState.classify(error), error)

    def testCacheRoundTrip(self):
        """
        states survive a save/load cycle and the age decides staleness
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "update_states.json"
            cache = UpdateStateCache(cache_path=cache_path)
            self.assertTrue(cache.is_stale)
            cache.states["wikidata-main"] = UpdateState(
                endpoint_name="wikidata-main",
                triples=8978336212,
                success=True,
                status=UpdateState.OK,
                checked="2026-09-23T10:00:00",
            )
            cache.refreshed = "2026-09-23T10:00:00"
            cache.save()

            reloaded = UpdateStateCache(cache_path=cache_path)
            state = reloaded.get("wikidata-main")
            self.assertIsNotNone(state)
            self.assertEqual(8978336212, state.triples)
            self.assertEqual(UpdateState.OK, state.status)

    def testRefreshIsReal(self):
        """
        the refresh runs real queries against the configured endpoints
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "update_states.json"
            cache = UpdateStateCache(cache_path=cache_path)
            em = Endpoints()
            states = cache.refresh(em, force=True)
            ok_states = [s for s in states.values() if s.status == UpdateState.OK]
            debug = self.debug
            if debug:
                for key, state in states.items():
                    print(f"{key}: {state.status} {state.triples} {state.error or ''}")
            self.assertTrue(states)
            self.assertTrue(ok_states, "at least one endpoint must answer")
            for state in ok_states:
                self.assertIsNotNone(state.checked)
            self.assertFalse(cache.is_stale)
            self.assertTrue(cache_path.exists())
