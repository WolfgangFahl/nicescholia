# Adjust this import based on where you saved the provided ListOfDictsGrid code
# Example: from nscholia.lod_grid import ListOfDictsGrid, GridConfig
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from nscholia.endpoints import Endpoints
from nscholia.monitor import Monitor


class Dashboard:
    """
    UI for monitoring endpoints using ListOfDictsGrid.
    """

    def __init__(self, solution):
        self.solution = solution
        self.webserver = solution.webserver
        self.grid = None  # Will hold the ListOfDictsGrid instance

        # Initialize the endpoints provider
        self.endpoints_provider = Endpoints()

    async def check_all(self):
        """Run checks for all endpoints in the grid"""
        if not self.grid:
            return

        ui.notify("Checking endpoints...")

        # Access the List of Dicts (LOD) directly from the wrapper
        rows = self.grid.lod

        for row in rows:
            # Visual update extracting checking state
            row["status"] = "Checking..."
            row["color"] = "#f0f0f0"  # Light gray

            # Update the grid view to show 'Checking...' state immediately
            self.grid.update()

            # Async check
            # row['url'] contains the SPARQL endpoint URL
            try:
                result = await Monitor.check(row["url"])

                # Update result
                if result.is_online:
                    row["status"] = f"Online ({result.status_code})"
                    row["latency"] = result.latency
                    row["color"] = "#d1fae5"  # light green
                else:
                    row["status"] = result.error or f"Error {result.status_code}"
                    row["latency"] = 0
                    row["color"] = "#fee2e2"  # light red
            except Exception as ex:
                row["status"] = str(ex)
                row["color"] = "#fee2e2"

        # Final update to show results
        self.grid.update()
        ui.notify("Status check complete")

    def setup_ui(self):
        """
        Render the dashboard
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Endpoint Monitor").classes("text-2xl font-bold")
            ui.button("Refresh", icon="refresh", on_click=self.check_all)

        # 1. Fetch data
        endpoints_data = self.endpoints_provider.get_endpoints()

        rows = []
        for key, ep in endpoints_data.items():
            # Prefer checking the website URL over the SPARQL endpoint
            # SPARQL endpoints often don't respond well to simple GET requests
            check_url = getattr(ep, "website", None)
            if not check_url:
                # Fall back to endpoint if no website is available
                check_url = getattr(ep, "endpoint", getattr(ep, "url", ""))

            ep_url = getattr(ep, "endpoint", getattr(ep, "url", ""))
            ep_name = getattr(ep, "name", key)
            ep_group = getattr(ep, "group", "General")

            link_html = Link.create(check_url if hasattr(ep, "website") else ep_url, "Link")

            rows.append(
                {
                    "group": ep_group,
                    "name": ep_name,
                    "url": check_url,  # URL to check for availability
                    "endpoint_url": ep_url,  # Original SPARQL endpoint
                    "link": link_html,
                    "status": "Pending",
                    "latency": 0.0,
                    "color": "#ffffff",
                }
            )

        column_defs = [
            {"headerName": "Group", "field": "group", "rowGroup": True, "hide": True},
            {
                "headerName": "Service",
                "field": "name",
                "sortable": True,
                "filter": True,
                "flex": 2,
            },
            {
                "headerName": "URL",
                "field": "link",
                "width": 70,
            },
            {"headerName": "Status", "field": "status", "sortable": True, "flex": 1},
            {
                "headerName": "Latency (s)",
                "field": "latency",
                "sortable": True,
                "width": 120,
                "type": "numericColumn",
            },
        ]

        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            ":getRowStyle": """(params) => {
                return { background: params.data.color };
            }""",
        }

        config = GridConfig(
            column_defs=column_defs,
            key_col="url",
            options=grid_options,
            html_columns=[2],
            auto_size_columns=True,
            theme="balham",
        )

        self.grid = ListOfDictsGrid(lod=rows, config=config)
        ui.timer(0.5, self.check_all, once=True)