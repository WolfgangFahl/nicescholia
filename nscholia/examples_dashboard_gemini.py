"""
Created on 2025-12-19

@author: wf
"""

import asyncio

import pandas as pd
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from nicegui import run, ui

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet.
    Includes background loading, progress tracking, and separate reload capabilities.
    """

    def __init__(self, solution, sheet: GoogleSheet):
        super().__init__(solution)
        # We rely on the webserver to hold the sheet config and cached data
        self.webserver = solution.webserver
        self.progress_bar = None
        self.grid_container = None

        # Extend colors for specific states if needed
        self.COLORS.update({"pending": "#ffffff", "checking": "#f0f0f0"})

    def setup_ui(self):
        """
        Setup the Dashboard UI elements.
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Scholia Examples").classes("text-2xl font-bold")

            # Action Buttons
            with ui.row().classes("gap-2"):
                ui.button(
                    "Reload Sheet", icon="refresh", on_click=self.reload_sheet
                ).props("outline")
                ui.button("Check Links", icon="network_check", on_click=self.check_all)

                if hasattr(self.webserver, "sheet_id"):
                    ui.link(
                        "Source Sheet",
                        f"https://docs.google.com/spreadsheets/d/{self.webserver.sheet_id}",
                        new_tab=True,
                    ).classes("text-sm text-blue-500 self-center ml-2")

            # Legend from base class
            self.setup_legend()

        # Progress bar
        self.progress_bar = NiceguiProgressbar(total=100, desc="Status", unit="%")
        self.progress_bar.progress.visible = False

        # Grid container
        self.grid_container = ui.column().classes("w-full h-full")

        # Load data: reuse cached data if available, else load from sheet
        if getattr(self.webserver, "sheet_data", None):
            self.render_grid(self.webserver.sheet_data)
        else:
            # Trigger load in background after UI setup
            ui.timer(0.1, self.reload_sheet, once=True)

    async def reload_sheet(self):
        """
        Reload data from the Google Sheet in the background.
        """
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description("Loading Sheet Data...")
        self.progress_bar.update(0)

        try:
            # Use run.io_bound to avoid blocking the event loop with pandas I/O
            if hasattr(self.webserver, "sheet"):
                data = await run.io_bound(self.webserver.sheet.as_lod)
                self.webserver.sheet_data = data  # Cache the data
                self.render_grid(data)
                ui.notify(f"Successfully loaded {len(data)} examples")
            else:
                ui.notify("Sheet configuration missing", type="negative")

        except Exception as e:
            ui.notify(f"Error loading sheet: {str(e)}", type="negative")
            self.solution.handle_exception(e)
        finally:
            self.progress_bar.progress.visible = False

    def render_grid(self, raw_data: list):
        """
        Transform raw data and render the AG Grid.
        """
        self.grid_container.clear()

        rows = []
        for item in raw_data:
            link_url = item.get("link")

            # Basic validation
            if (
                pd.isna(link_url)
                or not isinstance(link_url, str)
                or not link_url.startswith("http")
            ):
                continue

            # Create clickable link
            link_html = Link.create(link_url, "View")

            # Safe extraction of fields
            def get_val(key, default=""):
                val = item.get(key, default)
                return str(val) if not pd.isna(val) else default

            rows.append(
                {
                    "raw_link": link_url,
                    "link_col": link_html,
                    "comment": get_val("comment"),
                    "sheet_status": get_val("status", "-"),
                    "pr": get_val("PR"),
                    "github1": get_val("GitHub ticket 1"),
                    "error1": get_val("error message 1"),
                    "live_status": "Pending",
                    "latency": 0.0,
                    "color": self.COLORS["pending"],
                }
            )

        column_defs = [
            {
                "headerName": "Link",
                "field": "link_col",
                "width": 70,
                "cellRenderer": "html",
            },
            {
                "headerName": "Comment",
                "field": "comment",
                "flex": 2,
                "wrapText": True,
                "autoHeight": True,
            },
            {"headerName": "Sheet Status", "field": "sheet_status", "width": 100},
            {"headerName": "PR", "field": "pr", "width": 90},
            {"headerName": "Live Check", "field": "live_status", "width": 160},
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
            html_columns=[0],
            auto_size_columns=True,
            theme="balham",
        )

        with self.grid_container:
            self.grid = ListOfDictsGrid(lod=rows, config=config)

    async def check_all(self):
        """
        Check all links in the grid asynchronously with progress updates.
        """
        if not self.grid:
            return

        rows = self.grid.lod
        total = len(rows)

        # Prepare progress bar
        self.progress_bar.total = total
        self.progress_bar.value = 0
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description(f"Checking {total} links...")

        # Reset states visually first
        for row in rows:
            row["live_status"] = "Queued..."
            row["color"] = self.COLORS["checking"]
        self.grid.update()

        # Process in batches to keep UI responsive and limit concurrency
        batch_size = 10

        for i in range(0, total, batch_size):
            batch_rows = rows[i : i + batch_size]
            tasks = [self.check_single_row(row) for row in batch_rows]

            # Run batch concurrently
            await asyncio.gather(*tasks)

            # Update progress
            self.progress_bar.update(len(batch_rows))

            # Periodically update grid (prevent too many redraws)
            self.grid.update()

        self.progress_bar.progress.visible = False
        ui.notify("Link checking complete")

    async def check_single_row(self, row: dict):
        """
        Check a single row's URL and update the row dictionary.
        """
        url = row.get("raw_link")
        if not url:
            return

        try:
            row["live_status"] = "Checking..."
            # Monitor.check should be async and non-blocking
            result = await Monitor.check(url)

            if result.is_online:
                row["latency"] = result.latency
                row["live_status"] = f"OK ({result.status_code})"
                row["color"] = self.COLORS["success"]
            else:
                row["latency"] = 0
                error_info = result.error or f"Http {result.status_code}"
                row["live_status"] = error_info
                row["color"] = self.COLORS["error"]

        except Exception as ex:
            row["live_status"] = "Exception"
            row["latency"] = 0
            row["color"] = self.COLORS["error"]
