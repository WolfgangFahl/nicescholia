"""
Webserver definition
"""

from ngwidgets.input_webserver import InputWebserver, InputWebSolution, WebserverConfig
from nicegui import Client, ui
from nscholia.version import Version

from nscholia.endpoint_dashboard import EndpointDashboard
from nscholia.examples_dashboard_gemini import ExampleDashboard as ExampleDashboardGemini
from nscholia.examples_dashboard_chatgpt import ExampleDashboard as ExampleDashboardChatGPT
from nscholia.examples_dashboard_grok4 import ExampleDashboard as ExampleDashboardGrok4
from nscholia.examples_dashboard_claude import ExampleDashboard as ExampleDashboardClaude


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

        @ui.page("/examples")
        async def examples(client: Client):
            return await self.page(client, ScholiaSolution.examples)

    def configure_run(self):
        """
        configure me
        """
        super().configure_run()
        self.sheet_id = self.args.sheet_id
        self.sheet_gid = self.args.sheet_gid


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
            self.link_button("Endpoints", "/", "endpoint dashboard")
            self.link_button("Examples", "/examples", "examples dashboard")
            # Example of external link
            self.link_button(
                "GitHub",
                "https://github.com/WolfgangFahl/nicescholia",
                "code",
                new_tab=True,
            )

    async def examples(self):
        """
        Examples page using Google Sheet with selector for different dashboards
        """
        async def show():
            # Define the dashboard options
            dashboard_options = {
                "Gemini": ExampleDashboardGemini,
                "ChatGPT": ExampleDashboardChatGPT,
                "Grok4": ExampleDashboardGrok4,
                "Claude": ExampleDashboardClaude,
            }

            # UI for selector
            with ui.row().classes("w-full items-center mb-4"):
                ui.label("Select Dashboard:").classes("mr-2")
                selector = ui.select(
                    list(dashboard_options.keys()),
                    value=list(dashboard_options.keys())[0],  # Default to first
                    on_change=lambda e: self.update_dashboard(e.value, dashboard_options)
                ).classes("w-32")

            # Container for the dashboard
            self.dashboard_container = ui.element("div").classes("w-full")

            # Initial load
            await self.update_dashboard(selector.value, dashboard_options)

        await self.setup_content_div(show)

    async def update_dashboard(self, selected: str, options: dict):
        """
        Update the displayed dashboard based on selection
        """
        if self.selected_dashboard:
            self.selected_dashboard = None  # Clear previous

        dashboard_cls = options.get(selected)
        if not dashboard_cls:
            ui.notify(f"Invalid selection: {selected}", type="error")
            return

        with self.dashboard_container:
            self.dashboard_container.clear()
            self.selected_dashboard = dashboard_cls(
                self,
                sheet_id=self.webserver.sheet_id,
                gid=self.webserver.sheet_gid
            )
            self.selected_dashboard.setup_ui()

    async def home(self):
        """
        The main page content
        """

        def show():
            # Instantiate the View Component
            self.endpoint_dashboard = EndpointDashboard(self)
            self.endpoint_dashboard.setup_ui()

        await self.setup_content_div(show)
