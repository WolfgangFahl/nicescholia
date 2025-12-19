"""
Webserver definition
"""

from ngwidgets.input_webserver import InputWebserver, InputWebSolution, WebserverConfig
from nicegui import Client, ui
from nscholia.version import Version

from nscholia.backend import Backends
from nscholia.backend_dashboard import BackendDashboard
from nscholia.endpoint_dashboard import EndpointDashboard
from nscholia.examples_dashboard import ExampleDashboard
from nscholia.google_sheet import GoogleSheet


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

        @ui.page("/examples")
        async def examples(client: Client):
            return await self.page(client, ScholiaSolution.examples)

        @ui.page("/backends")
        async def backends(client: Client):
            return await self.page(client, ScholiaSolution.backends)


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
            self.backends=Backends.from_yaml_path()
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
