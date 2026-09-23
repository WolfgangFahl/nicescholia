"""
Created on 2025-12-19

@author: wf
"""

import asyncio

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from nscholia.dashboard import Dashboard
from nscholia.endpoints import UpdateState
from nscholia.monitor import Monitor


class EndpointDashboard(Dashboard):
    """
    UI for monitoring endpoints using ListOfDictsGrid.
    """

    def __init__(self, solution):
        super().__init__(solution)
        # endpoints and the daily refreshed update states live on the webserver
        self.endpoints_provider = self.webserver.endpoints
        self.update_state_cache = self.webserver.update_state_cache

    def show_state(self, row: dict, update_state: UpdateState):
        """
        show the given update state in the given row - the color is the
        outcome of the real SPARQL call, not of a website ping

        Args:
            row: the grid row to fill
            update_state: the measured state
        """
        row["triples"] = update_state.triples or 0
        row["checked"] = update_state.checked or ""
        if update_state.status == UpdateState.OK:
            row["status"] = "🟢 ok"
            row["timestamp"] = update_state.timestamp or ""
            row["color"] = self.COLORS["success"]
        elif update_state.status == UpdateState.QUERY_FAILED:
            row["status"] = f"🟡 query failed: {update_state.error or 'unknown'}"
            row["timestamp"] = ""
            row["color"] = self.COLORS["warning"]
        else:
            row["status"] = f"🔴 unreachable: {update_state.error or 'unknown'}"
            row["timestamp"] = ""
            row["color"] = self.COLORS["error"]

    def show_cached(self):
        """
        show the cached states - no query is run here
        """
        if not self.grid:
            return
        for row in self.grid.lod:
            update_state = self.update_state_cache.get(row["endpoint_key"])
            if update_state:
                self.show_state(row, update_state)
            else:
                row["status"] = "pending"
                row["color"] = self.COLORS["checking"]
        self.grid.update()

    async def check_all(self):
        """
        measure all endpoints with a real query and show the result
        """
        if not self.grid:
            return

        ui.notify("Checking endpoints ...")
        for row in self.grid.lod:
            row["status"] = "checking ..."
            row["color"] = self.COLORS["checking"]
        self.grid.update()

        # latency of the website of each endpoint - informational only
        for row in self.grid.lod:
            try:
                result = await Monitor.check(row["url"])
                row["latency"] = result.latency
            except Exception:
                row["latency"] = 0

        await asyncio.get_event_loop().run_in_executor(
            None,
            self.update_state_cache.refresh,
            self.endpoints_provider,
            True,
        )
        self.show_cached()
        ui.notify("Status check complete")

    def setup_ui(self):
        """
        Render the dashboard
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Endpoint Monitor").classes("text-2xl font-bold")
            ui.button("Refresh", icon="refresh", on_click=self.check_all)
            self.setup_legend()

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
                    "status": "pending",
                    "latency": 0.0,
                    "triples": 0,
                    "timestamp": "",
                    "checked": "",
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
            {
                "headerName": "Measured",
                "field": "checked",
                "sortable": True,
                "width": 170,
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
        # show what the daily refresh measured - Refresh runs a live check
        self.show_cached()
