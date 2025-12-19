"""
Created on 2025-12-19

@author: wf
"""

import pandas as pd
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet
    """

    # Extend COLORS with a default/pending state
    COLORS = {
        **Dashboard.COLORS,
        "pending": "#ffffff",
    }  # White for initial pending state

    def __init__(self, solution, sheet_id: str, gid: int):
        super().__init__(solution)
        self.sheet_id = sheet_id
        self.sheet = GoogleSheet(sheet_id=self.sheet_id, gid=gid)
        self.sheet_rows = None

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

    def load_sheet(self):
        # Load data
        try:
            self.sheet_rows = self.sheet.as_lod()
        except Exception as ex:
            self.solution.handle_exception(ex)

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

        # Transform data for grid
        rows = []
        if not self.sheet_rows:
            ui.notify("sheet data not loaded ")
            return
        for item in self.sheet_rows:
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

            # Additional columns from sheet
            pr = item.get("PR", "")
            if pd.isna(pr):
                pr = ""

            error1 = item.get("error message 1", "")
            if pd.isna(error1):
                error1 = ""

            github1 = item.get("GitHub ticket 1", "")
            if pd.isna(github1):
                github1 = ""

            error2 = item.get("error message 2", "")
            if pd.isna(error2):
                error2 = ""

            github2 = item.get("GitHub ticket 2", "")
            if pd.isna(github2):
                github2 = ""

            error3 = item.get("error message 3", "")
            if pd.isna(error3):
                error3 = ""

            github3 = item.get("GitHub ticket 3", "")
            if pd.isna(github3):
                github3 = ""

            rows.append(
                {
                    "raw_link": link_url,
                    "link_col": link_html,
                    "comment": comment,
                    "sheet_status": str(orig_status),
                    "pr": pr,
                    "error1": error1,
                    "github1": github1,
                    "error2": error2,
                    "github2": github2,
                    "error3": error3,
                    "github3": github3,
                    "live_status": "Pending",
                    "latency": 0.0,
                    "color": self.COLORS["pending"],
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
            {"headerName": "PR", "field": "pr", "width": 100},
            {
                "headerName": "Error 1",
                "field": "error1",
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
            },
            {"headerName": "GitHub 1", "field": "github1", "width": 150},
            {
                "headerName": "Error 2",
                "field": "error2",
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
            },
            {"headerName": "GitHub 2", "field": "github2", "width": 150},
            {
                "headerName": "Error 3",
                "field": "error3",
                "flex": 1,
                "wrapText": True,
                "autoHeight": True,
            },
            {"headerName": "GitHub 3", "field": "github3", "width": 150},
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
