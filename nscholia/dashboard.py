import asyncio

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from nscholia.endpoints import Endpoints, UpdateState
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
            # Visual update for checking state
            row["status"] = "Checking..."
            row["color"] = "#f0f0f0"  # Light gray
            row["triples"] = 0
            row["timestamp"] = ""

            # Update the grid view to show 'Checking...' state immediately
            self.grid.update()

            # Async check
            try:
                url = row["url"]
                # First check if endpoint is online
                result = await Monitor.check(url)

                # Update basic availability result
                if result.is_online:
                    row["status"] = f"Online ({result.status_code})"
                    row["latency"] = result.latency
                    row["color"] = "#d1fae5"  # light green

                    # Now get update state information (triples & timestamp)
                    ep_key = row["endpoint_key"]
                    endpoints_data = self.endpoints_provider.get_endpoints()

                    if ep_key in endpoints_data:
                        ep = endpoints_data[ep_key]
                        # Run update state query in executor to avoid blocking
                        update_state = await asyncio.get_event_loop().run_in_executor(
                            None, UpdateState.from_endpoint, self.endpoints_provider, ep
                        )

                        if update_state.success:
                            row["triples"] = update_state.triples or 0
                            row["timestamp"] = update_state.timestamp or ""
                        else:
                            row["triples"] = 0
                            row["timestamp"] = update_state.error or "N/A"
                            # Optionally adjust status if update query failed
                            if update_state.error:
                                row[
                                    "status"
                                ] += f" (Update query: {update_state.error})"
                else:
                    row["status"] = result.error or f"Error {result.status_code}"
                    row["latency"] = 0
                    row["triples"] = 0
                    row["timestamp"] = ""
                    row["color"] = "#fee2e2"  # light red

            except Exception as ex:
                row["status"] = str(ex)
                row["latency"] = 0
                row["triples"] = 0
                row["timestamp"] = ""
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
            check_url = getattr(ep, "website", None)
            if not check_url:
                check_url = getattr(ep, "endpoint", getattr(ep, "url", ""))

            ep_url = getattr(ep, "endpoint", getattr(ep, "url", ""))
            ep_name = getattr(ep, "name", key)
            ep_group = getattr(ep, "group", "General")

            link_html = Link.create(
                check_url if hasattr(ep, "website") else ep_url, "Link"
            )

            rows.append(
                {
                    "group": ep_group,
                    "name": ep_name,
                    "url": check_url,  # URL to check for availability
                    "endpoint_url": ep_url,  # Original SPARQL endpoint
                    "endpoint_key": key,  # Store the key for later lookup
                    "link": link_html,
                    "status": "Pending",
                    "latency": 0.0,
                    "triples": 0,
                    "timestamp": "",
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
            {
                "headerName": "Status",
                "field": "status",
                "sortable": True,
                "flex": 2,
            },
            {
                "headerName": "Latency (s)",
                "field": "latency",
                "sortable": True,
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": "params.value ? params.value.toFixed(3) : '0.000'",
            },
            {
                "headerName": "Triples",
                "field": "triples",
                "sortable": True,
                "width": 130,
                "type": "numericColumn",
                "valueFormatter": "params.value ? params.value.toLocaleString() : '0'",
            },
            {
                "headerName": "Last Update",
                "field": "timestamp",
                "sortable": True,
                "width": 200,
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
