"""
Webserver definition
"""

from ngwidgets.input_webserver import InputWebserver, InputWebSolution, WebserverConfig
from nicegui import client

from nscholia.dashboard import Dashboard
from nscholia.version import Version


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


class ScholiaSolution(InputWebSolution):
    """
    Handling specific page requests for a client session.
    """

    def __init__(self, webserver, client: client):
        super().__init__(webserver, client)

    def setup_menu(self, detailed: bool = True):
        """
        Configure the navigation menu
        """
        # Call safe setup from parent
        super().setup_menu(detailed=detailed)

        # Add custom links
        with self.header:
            self.link_button("Dashboard", "/", "dashboard")
            # Example of external link
            self.link_button(
                "GitHub",
                "https://github.com/WolfgangFahl/nicescholia",
                "code",
                new_tab=True,
            )

    async def home(self):
        """
        The main page content
        """

        def show():
            # Instantiate the View Component
            self.dashboard = Dashboard(self)
            self.dashboard.setup_ui()

        await self.setup_content_div(show)
