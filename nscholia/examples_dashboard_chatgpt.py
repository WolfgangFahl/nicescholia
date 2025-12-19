'''
Created on 2025-12-19

@author: wf
'''
import pandas as pd
from nicegui import ui
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet.
    """

    def __init__(self, solution, sheet_id: str, gid: int):
        super().__init__(solution)
        self.sheet_id = sheet_id
        self.sheet = GoogleSheet(sheet_id=self.sheet_id, gid=gid)

    async def check_all(self):
        """
        Check reachability of all links in the grid.
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
                result = await Monitor.check(url)

                if getattr(result, "is_online", False):
                    row["latency"] = getattr(result, "latency", 0.0) or 0.0
                    status_code = getattr(result, "status_code", 200)
                    row["live_status"] = f"OK ({status_code})"
                    row["color"] = self.COLORS["success"]
                else:
                    status_code = getattr(result, "status_code", None)
                    error_msg = getattr(result, "error", None)
                    row["latency"] = 0.0
                    row["live_status"] = error_msg or (f"Error {status_code}" if status_code else "Offline")
                    row["color"] = self.COLORS["error"]
            except Exception as ex:
                row["latency"] = 0.0
                row["live_status"] = f"Ex: {ex}"
                row["color"] = self.COLORS["error"]

        self.grid.update()
        ui.notify("Example checks complete.")

    def setup_ui(self):
        """
        Setup grid with Google Sheet data.
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.button("Check all", icon="refresh", on_click=self.check_all)
            ui.link(
                "Source Sheet",
                f"https://docs.google.com/spreadsheets/d/{self.sheet_id}",
                new_tab=True,
            ).classes("text-sm text-blue-500")

        # Load data
        try:
            raw_data = self.sheet.as_lod()
        except Exception as e:
            ui.label(f"Error loading sheet: {e}").classes("text-red-500")
            return

        # Transform data for grid
        rows = []
        for item in raw_data:
            link_url = item.get("link")

            # Only process valid HTTP(S) links
            if pd.isna(link_url) or not isinstance(link_url, str) or not link_url.startswith("http"):
                continue

            link_html = Link.create(link_url, "View")

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
                    "color": self.COLORS["checking"],
                }
            )

        column_defs = [
            {"headerName": "Link", "field": "link_col", "width": 80},
            {"headerName": "Comment", "field": "comment", "flex": 2, "wrapText": True, "autoHeight": True},
            {"headerName": "Sheet Status", "field": "sheet_status", "width": 120, "tooltipField": "sheet_status"},
            {"headerName": "Live Check", "field": "live_status", "width": 160},
            {
                "headerName": "Latency (s)",
                "field": "latency",
                "width": 110,
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
            html_columns=[0],  # The link column contains HTML
            auto_size_columns=True,
            theme="balham",
        )

        self.grid = ListOfDictsGrid(lod=rows, config=config)

        # Auto-check after a brief delay
        ui.timer(1.0, self.check_all, once=True)
