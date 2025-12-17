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
            ep_url = getattr(ep, "endpoint", getattr(ep, "url", ""))
            ep_name = getattr(ep, "name", key)
            ep_group = getattr(ep, "group", "General")

            link_html = Link.create(ep_url, "Link")

            rows.append(
                {
                    "group": ep_group,
                    "name": ep_name,
                    "url": ep_url,
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
            },  # HTML rendered via html_columns
            {"headerName": "Status", "field": "status", "sortable": True, "flex": 1},
            {
                "headerName": "Latency (s)",
                "field": "latency",
                "sortable": True,
                "width": 120,
                "type": "numericColumn",
            },
        ]

        # Define styles and behavior in the options dictionary
        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            # This fixes the original error. We treat this as a standard AgGrid callback string.
            ":getRowStyle": """(params) => {
                return { background: params.data.color };
            }""",
        }

        # Configure the ListOfDictsGrid
        config = GridConfig(
            column_defs=column_defs,
            key_col="url",  # Use URL as the unique key
            options=grid_options,  # Pass the options mapping
            html_columns=[
                2
            ],  # Index of the 'link' column (0-based index of visible cols)
            auto_size_columns=True,
            theme="balham",  # Optional: 'ag-theme-balham' or 'material'
        )

        # Instantiate the grid wrapper
        self.grid = ListOfDictsGrid(lod=rows, config=config)

        # Trigger one check initially (optional)
        ui.timer(0.5, self.check_all, once=True)
