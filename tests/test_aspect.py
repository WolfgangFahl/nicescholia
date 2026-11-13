"""
Created on 2026-11-13

@author: wf
"""

from basemkit.basetest import Basetest
from ngwidgets.webserver_test import WebserverTest

from nscholia.aspect import AspectQueries
from nscholia.cmd import ScholiaCmd
from nscholia.webserver import ScholiaWebserver


class TestAspectQueries(Basetest):
    """
    Test the named parameterized queries of the aspects
    see https://github.com/WolfgangFahl/nicescholia/issues/16

    the expected results can falsify a walk but not verify it
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.aspect_queries = AspectQueries()

    def test_views(self):
        """
        test the views derived from the query names
        """
        views = self.aspect_queries.views()
        if self.debug:
            print(views)
        self.assertIn("author", views)
        self.assertIn("list-of-publications", views["author"])

    def test_select_columns(self):
        """
        test that the columns come from the SELECT clause of the query
        """
        query = self.aspect_queries.get_query("author_list-of-publications")
        columns = AspectQueries.select_columns(query.query)
        if self.debug:
            print(columns)
        expected = [
            "date",
            "work",
            "workLabel",
            "type",
            "pages",
            "venue",
            "venueLabel",
            "authors",
            "authorsUrl",
        ]
        self.assertEqual(expected, columns)

    def test_invalid_params(self):
        """
        test that parameter values that are no identifiers never reach a query
        """
        for params in [{"q": "Q80 . } #"}, {"limit": 0}, {"unknown": "Q80"}]:
            with self.assertRaises(ValueError):
                self.aspect_queries.run("author", "list-of-publications", params)

    def test_author_list_of_publications(self):
        """
        test the walk Scholar <-author P50- Paper for Tim Berners-Lee (Q80):
        at least 64 entries and Linked data - the story so far (Q29301445)
        is one of them
        """
        for endpoint_name in AspectQueries.ENDPOINT_NAMES:
            with self.subTest(endpoint_name=endpoint_name):
                count_result = self.aspect_queries.run(
                    "author",
                    "list-of-publications",
                    endpoint_name=endpoint_name,
                    count=True,
                )
                self.assertEqual({}, count_result.errors)
                count = int(count_result.rows[0]["count"])
                result = self.aspect_queries.run(
                    "author",
                    "list-of-publications",
                    {"q": "Q80", "limit": 1000},
                    endpoint_name=endpoint_name,
                )
                if self.debug:
                    print(f"{endpoint_name}: count {count} rows {len(result.rows)}")
                self.assertEqual({}, result.errors)
                self.assertEqual("Table", result.default_view)
                self.assertGreaterEqual(count, 64)
                self.assertEqual(count, len(result.rows))
                works = [row["work"] for row in result.rows]
                self.assertIn("http://www.wikidata.org/entity/Q29301445", works)

    def test_first_working_endpoint(self):
        """
        test that an endpoint that does not answer is skipped
        """
        result = self.aspect_queries.run(
            "author", "list-of-publications", endpoint_name="no-such-endpoint"
        )
        self.assertIsNone(result.endpoint_name)
        self.assertIn("no-such-endpoint", result.errors)
        result = self.aspect_queries.run("author", "list-of-publications")
        self.assertIsNotNone(result.endpoint_name)
        self.assertEqual(10, len(result.rows))


class TestAspectRoutes(WebserverTest):
    """
    Test the Scholia compatible routes
    see https://github.com/WolfgangFahl/nicescholia/issues/17
    """

    def setUp(self, debug=False, profile=True):
        WebserverTest.setUp(
            self, ScholiaWebserver, ScholiaCmd, debug=debug, profile=profile
        )

    def test_openapi_has_view(self):
        """
        test that /docs lists the REST twin of the view with its parameters
        """
        paths = self.ws.app.openapi()["paths"]
        path = "/api/author/list-of-publications/{pid}"
        self.assertIn(path, paths)
        names = [param["name"] for param in paths[path]["get"]["parameters"]]
        for name in ["pid", "limit", "endpoint"]:
            self.assertIn(name, names)

    def test_api_view(self):
        """
        test the REST twin of the list of publications of Q80
        """
        response = self.client.get("/api/author/list-of-publications/Q80?limit=5")
        self.assertEqual(200, response.status_code)
        result = response.json()
        if self.debug:
            print(result)
        self.assertEqual(5, len(result["rows"]))
        self.assertEqual("Table", result["default_view"])
        self.assertIn("work", result["columns"])

    def test_api_view_invalid_pid(self):
        """
        test that an invalid identifier is refused
        """
        response = self.client.get("/api/author/list-of-publications/Q80x")
        self.assertEqual(400, response.status_code)
