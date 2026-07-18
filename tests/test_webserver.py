"""
Created on 2026-07-18

@author: wf
"""

from ngwidgets.webserver_test import WebserverTest

from nscholia.cmd import ScholiaCmd
from nscholia.webserver import ScholiaWebserver


class TestScholiaWebserver(WebserverTest):
    """
    Test the nicescholia webserver REST API
    """

    def setUp(self, debug=False, profile=True):
        WebserverTest.setUp(
            self, ScholiaWebserver, ScholiaCmd, debug=debug, profile=profile
        )

    def test_openapi_has_entries(self):
        """
        test that the OpenAPI spec has nicescholia metadata and path entries
        see https://github.com/WolfgangFahl/nicescholia/issues/8
        """
        spec = self.ws.app.openapi()
        self.assertEqual("nicescholia", spec["info"]["title"])
        paths = spec["paths"]
        if self.debug:
            print(list(paths.keys()))
        for path in ["/api/version", "/api/backends"]:
            self.assertIn(path, paths)

    def test_api_version(self):
        """
        test the /api/version endpoint
        """
        response = self.client.get("/api/version")
        self.assertEqual(200, response.status_code)
        version_record = response.json()
        if self.debug:
            print(version_record)
        self.assertEqual("nicescholia", version_record["name"])
        self.assertTrue("version" in version_record)

    def test_api_backends(self):
        """
        test the /api/backends endpoint
        """
        response = self.client.get("/api/backends")
        self.assertEqual(200, response.status_code)
        backends_record = response.json()
        if self.debug:
            print(backends_record)
        self.assertTrue(len(backends_record) > 0)
        for _key, backend in backends_record.items():
            self.assertTrue("url" in backend)
