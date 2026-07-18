"""
Webserver definition
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any, Dict, List

from ngwidgets.input_webserver import InputWebserver, InputWebSolution, WebserverConfig
from nicegui import Client, app, ui

from nscholia.backend import Backends
from nscholia.backend_dashboard import BackendDashboard
from nscholia.endpoint_dashboard import EndpointDashboard
from nscholia.endpoints import Endpoints, UpdateState
from nscholia.examples_dashboard import ExampleDashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.version import Version

# Endpoint fields that must never be exposed via the REST API (credentials/
# internal connection details) - see SECURITY handling for /api/endpoints.
ENDPOINT_SECRET_FIELDS = {"auth", "user", "password", "host", "port"}


def compact(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drop keys whose value is None to avoid null-noise in JSON responses.
    """
    return {key: value for key, value in record.items() if value is not None}


class ScholiaWebserver(InputWebserver):
    """
    The main webserver class
    """

    @classmethod
    def get_config(cls) -> WebserverConfig:
        config = WebserverConfig(
            short_name="nicescholia",
            timeout=6.0,
            copy_right="(c) 2025 Wolfgang Fahl",
            version=Version(),
            default_port=9000,
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = ScholiaSolution
        return server_config

    def __init__(self):
        super().__init__(config=ScholiaWebserver.get_config())
        self.sheet = None
        self.backends = None
        self.endpoints = None
        version = self.config.version
        # OpenAPI metadata so /docs shows nicescholia instead of FastAPI defaults
        app.title = version.name
        app.version = version.version
        app.description = version.description

        @ui.page("/examples")
        async def examples(client: Client):
            return await self.page(client, ScholiaSolution.examples)

        @ui.page("/backends")
        async def backends(client: Client):
            return await self.page(client, ScholiaSolution.backends)

        @app.get("/api/version", tags=["nicescholia"])
        def api_version() -> Dict[str, Any]:
            """
            Get nicescholia version information.
            """
            version_record = {
                "name": version.name,
                "version": version.version,
                "date": version.date,
                "updated": version.updated,
                "description": version.description,
                "doc_url": version.doc_url,
                "cm_url": version.cm_url,
            }
            return version_record

        @app.get("/api/backends", tags=["nicescholia"])
        def api_backends(probe: bool = False, timeout: float = 2.0) -> Dict[str, Any]:
            """
            Get the configured Scholia mirror backends.

            Args:
                probe: if true, live-enrich each backend from its /backend
                    endpoint (concurrently) - mirrors the /backends GUI dashboard.
                timeout: per-backend request timeout in seconds when probing.

            Returns:
                mapping of backend key to its config; None fields are omitted
                to avoid null-noise (raw config has most fields unset).
            """
            return self.get_backends_record(probe=probe, timeout=timeout)

        @app.get("/api/endpoints", tags=["nicescholia"])
        def api_endpoints(probe: bool = False) -> Dict[str, Any]:
            """
            Get the configured SPARQL endpoints - REST counterpart of the
            endpoint (home) dashboard.

            Args:
                probe: if true, add the live UpdateState (triples, timestamp)
                    per endpoint - this runs SPARQL queries and is slow.

            Returns:
                mapping of endpoint key to a credential-stripped record; when
                probing, an "update_state" object is added per endpoint.
            """
            return self.get_endpoints_record(probe=probe)

        @app.get("/api/examples", tags=["nicescholia"])
        def api_examples() -> List[Dict[str, Any]]:
            """
            Get the Scholia example queries - REST counterpart of the
            examples dashboard. Returns an empty list if the source Google
            Sheet is not loaded.
            """
            return self.get_examples_record()

    def get_backends_record(
        self, probe: bool = False, timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Build the /api/backends response.

        Args:
            probe: live-enrich each backend from its /backend endpoint.
            timeout: per-backend request timeout in seconds when probing.
        """
        if self.backends is None:
            self.backends = Backends.from_yaml_path()
        backends = self.backends.backends
        if probe and backends:
            with ThreadPoolExecutor(max_workers=len(backends)) as executor:
                for backend in backends.values():
                    executor.submit(backend.fetch_config, timeout)
        backends_record = {
            key: compact(asdict(backend)) for key, backend in backends.items()
        }
        return backends_record

    def get_endpoints_record(self, probe: bool = False) -> Dict[str, Any]:
        """
        Build the /api/endpoints response with credential fields removed.

        Args:
            probe: add the live UpdateState (triples, timestamp) per endpoint.
        """
        if self.endpoints is None:
            self.endpoints = Endpoints()
        endpoints = self.endpoints.get_endpoints()
        endpoints_record = {}
        for key, ep in endpoints.items():
            record = compact(asdict(ep))
            for secret in ENDPOINT_SECRET_FIELDS:
                record.pop(secret, None)
            if probe:
                update_state = UpdateState.from_endpoint(self.endpoints, ep)
                record["update_state"] = compact(asdict(update_state))
            endpoints_record[key] = record
        return endpoints_record

    def get_examples_record(self) -> List[Dict[str, Any]]:
        """
        Build the /api/examples response from the preloaded Google Sheet.
        Returns an empty list when the sheet is not available.
        """
        if not self.sheet or not getattr(self.sheet, "lod", None):
            return []
        examples = []
        for item in self.sheet.lod:
            link = item.get("link", "")
            if not link or not str(link).startswith("http"):
                continue
            examples.append(
                {
                    "link": link,
                    "comment": item.get("comment", ""),
                    "status": item.get("status", ""),
                    "pr": item.get("PR", ""),
                }
            )
        return examples

    def configure_run(self):
        """
        configure me
        """
        super().configure_run()
        self.sheet_id = self.args.sheet_id
        self.sheet_gid = self.args.sheet_gid
        # Preload sheet on server startup for better performance
        try:
            self.sheet = GoogleSheet(sheet_id=self.sheet_id, gid=self.sheet_gid)
            self.sheet.as_lod()
            print(f"Preloaded Google Sheet: {len(self.sheet.lod)} rows")
        except Exception as ex:
            # Non-fatal: UI can still load/reload on demand
            print(f"Sheet preload failed: {ex}")
        # Preload backends on server startup
        try:
            self.backends = Backends.from_yaml_path()
        except Exception as ex:
            print(f"Backends preload failed: {ex}")


class ScholiaSolution(InputWebSolution):
    """
    Handling specific page requests for a client session.
    """

    def __init__(self, webserver, client: Client):
        super().__init__(webserver, client)
        self.selected_dashboard = None  # To hold the current dashboard instance

    def setup_menu(self, detailed: bool = True):
        """
        Configure the navigation menu
        """
        # Call safe setup from parent
        super().setup_menu(detailed=detailed)

        # Add custom links
        with self.header:
            self.link_button("Endpoints", "/", "hub")
            self.link_button("Examples", "/examples", "table_view")
            self.link_button("Backends", "/backends", "dns")
            # Example of external link
            # self.link_button(
            #    "GitHub",
            #    "https://github.com/WolfgangFahl/nicescholia",
            #    "code",
            #    new_tab=True,
            # )

    async def examples(self):
        """
        Examples page using Google Sheet with selector for different dashboards
        """

        async def show():
            self.dashboard = ExampleDashboard(self, sheet=self.webserver.sheet)
            self.dashboard.setup_ui()

        await self.setup_content_div(show)

    async def backends(self):
        """
        Backends status page
        """

        async def show():
            # No path arg needed here, it uses the class default from Backends
            self.dashboard = BackendDashboard(self)
            self.dashboard.setup_ui()

        await self.setup_content_div(show)

    async def home(self):
        """
        The main page content
        """

        def show():
            # Instantiate the View Component
            self.endpoint_dashboard = EndpointDashboard(self)
            self.endpoint_dashboard.setup_ui()

        await self.setup_content_div(show)
