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
        for path in [
            "/api/version",
            "/api/backends",
            "/api/endpoints",
            "/api/examples",
        ]:
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

    def test_api_backends_no_null_noise(self):
        """
        test that /api/backends omits None fields (no null-noise)
        see https://github.com/WolfgangFahl/nicescholia/issues/10
        """
        response = self.client.get("/api/backends")
        self.assertEqual(200, response.status_code)
        backends_record = response.json()
        for _key, backend in backends_record.items():
            for field, value in backend.items():
                self.assertIsNotNone(value, f"{field} should be omitted when None")

    def test_api_endpoints(self):
        """
        test the /api/endpoints endpoint (API parity with the endpoint dashboard)
        see https://github.com/WolfgangFahl/nicescholia/issues/10
        """
        response = self.client.get("/api/endpoints")
        self.assertEqual(200, response.status_code)
        endpoints_record = response.json()
        if self.debug:
            print(list(endpoints_record.keys()))
        self.assertTrue(len(endpoints_record) > 0)
        for _key, endpoint in endpoints_record.items():
            self.assertIn("name", endpoint)
            self.assertIn("endpoint", endpoint)
            # SECURITY: credentials must never be exposed via the API
            for secret in ["auth", "user", "password", "host", "port"]:
                self.assertNotIn(secret, endpoint)

    def test_api_examples(self):
        """
        test the /api/examples endpoint (API parity with the examples dashboard)
        see https://github.com/WolfgangFahl/nicescholia/issues/10
        """
        response = self.client.get("/api/examples")
        self.assertEqual(200, response.status_code)
        examples_record = response.json()
        if self.debug:
            print(f"{len(examples_record)} examples")
        self.assertIsInstance(examples_record, list)
