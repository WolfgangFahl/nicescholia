"""
Created on 2025-12-19

@author: wf
"""
import pandas as pd
from nicegui import ui
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet
    """

    def __init__(self, solution, sheet_id: str, gid: int):
        super().__init__(solution)
        self.sheet_id = sheet_id
        self.gid = gid
        self.sheet = GoogleSheet(sheet_id=self.sheet_id, gid=self.gid)

    async def check_all(self):
        """
        Check reachability of all links in the grid
        """
        if not self.grid:
            return

        ui.notify("Checking example links...")

        rows = self.grid.lod
        for row in rows:
            url = row.get("raw_link")

            if not url:
                continue

            row["live_status"] = "Checking..."
            row["color"] = self.COLORS["checking"]
            self.grid.update()

            try:
                # Check the specific link
                result = await Monitor.check(url)

                if result.is_online:
                    row["latency"] = result.latency
                    row["live_status"] = f"OK ({result.status_code})"
                    row["color"] = self.COLORS["success"]
                else:
                    row["latency"] = 0
                    row["live_status"] = result.error or f"Error {result.status_code}"
                    row["color"] = self.COLORS["error"]

            except Exception as ex:
                row["live_status"] = f"Ex: {str(ex)}"
                row["color"] = self.COLORS["error"]

        self.grid.update()
        ui.notify("Example checks complete.")

    def setup_ui(self):
        """
        Setup grid with Google Sheet data
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.button("Refresh", icon="refresh", on_click=self.check_all)
            ui.link(
                "Source Sheet",
                f"https://docs.google.com/spreadsheets/d/{self.sheet_id}",
                new_tab=True,
            ).classes("text-sm text-blue-500")

        # Load data
        try:
            raw_data = self.sheet.as_lod()
        except Exception as e:
            ui.label(f"Error loading sheet: {str(e)}").classes("text-red-500")
            return

        # Transform data for grid
        rows = []
        for item in raw_data:
            link_url = item.get("link")

            # Simple validation - only process if we have a valid link string
            if (
                pd.isna(link_url)
                or not isinstance(link_url, str)
                or not link_url.startswith("http")
            ):
                continue

            # Create clickable link
            link_html = Link.create(link_url, "View")

            # Extract relevant columns gracefully
            comment = item.get("comment", "")
            if pd.isna(comment):
                comment = ""

            orig_status = item.get("status", "")
            if pd.isna(orig_status):
                orig_status = "-"

            rows.append(
                {
                    "raw_link": link_url,
                    "link_col": link_html,
                    "comment": comment,
                    "sheet_status": str(orig_status),
                    "live_status": "Pending",
                    "latency": 0.0,
                    # Initial white color (manual hex since base class lacks 'white' key)
                    "color": "#ffffff",
                }
            )

        column_defs = [
            {"headerName": "Link", "field": "link_col", "width": 70},
            {
                "headerName": "Comment",
                "field": "comment",
                "flex": 2,
                "wrapText": True,
                "autoHeight": True,
            },
            {
                "headerName": "Sheet Status",
                "field": "sheet_status",
                "width": 100,
                "tooltipField": "sheet_status",
            },
            {"headerName": "Live Check", "field": "live_status", "width": 150},
            {
                "headerName": "Latency (s)",
                "field": "latency",
                "width": 100,
                "type": "numericColumn",
                "valueFormatter": "params.value ? params.value.toFixed(3) : ''",
            },
        ]

        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            "getRowStyle": """function(params) { return { background: params.data.color }; }""",
        }

        config = GridConfig(
            column_defs=column_defs,
            key_col="raw_link",
            options=grid_options,
            html_columns=[0],  # The link column
            auto_size_columns=True,
            theme="balham",
        )

        self.grid = ListOfDictsGrid(lod=rows, config=config)

        # Auto-check after a brief delay
        ui.timer(1.0, self.check_all, once=True)