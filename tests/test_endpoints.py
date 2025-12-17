"""
Created on 17.12.2025

@author: wf
"""

from basemkit.basetest import Basetest

from nscholia.endpoints import Endpoints


class TestEndpoints(Basetest):
    """
    test endpoints
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testEndpoints(self):
        """
        test endpoint loading
        """
        debug = self.debug
        debug = True
        endpoints = Endpoints().get_endpoints()
        for ep_name, ep in endpoints.items():
            if debug:
                print(ep)
                pass
