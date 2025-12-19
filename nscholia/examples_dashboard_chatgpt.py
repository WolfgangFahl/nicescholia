"""
Created on 2025-12-19

@author: wf
"""

import asyncio

import pandas as pd
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from nicegui import background_tasks, ui

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet.
    """

    COLORS = {
        **Dashboard.COLORS,
        "pending": "#ffffff",
    }

    def __init__(self, solution, sheet: GoogleSheet):
        super().__init__(solution)
        self.sheet = sheet
        self.progress_bar: NiceguiProgressbar | None = None

    def setup_legend(self):
        # Override: proper color boxes matching state
        def chip(color: str, label: str):
            with ui.row().classes("items-center gap-1"):
                ui.element("div").style(
                    f"width:12px;height:12px;border-radius:3px;background:{color}"
                )
                ui.label(label).classes("text-xs")

        with ui.row().classes("ml-auto gap-3"):
            chip(self.COLORS["pending"], "Pending")
            chip(self.COLORS["checking"], "Checking")
            chip(self.COLORS["success"], "Success")
            chip(self.COLORS["warning"], "Warning")
            chip(self.COLORS["error"], "Error")

    async def reload_sheet_async(self):
        """Reload sheet in background via webserver cache, then rebuild grid."""
        try:
            ok, info = await asyncio.to_thread(self.solution.webserver.reload_sheet)
            if ok:
                self.sheet.as_lod()
                ui.notify(f"Reloaded sheet: {info} rows")
                self.build_or_refresh_grid()
            else:
                ui.notify(f"Reload failed: {info}", type="negative")
        except Exception as ex:
            ui.notify(f"Reload error: {ex}", type="negative")

    def build_or_refresh_grid(self):
        """Build grid from self.sheet (or refresh if grid exists)."""
        rows = []
        for item in self.sheet.lod or []:
            link_url = item.get("link")
            if (
                pd.isna(link_url)
                or not isinstance(link_url, str)
                or not link_url.startswith("http")
            ):
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
                    "color": self.COLORS["pending"],
                }
            )

        column_defs = [
            {"headerName": "Link", "field": "link_col", "width": 80},
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
                "width": 120,
                "tooltipField": "sheet_status",
            },
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
            html_columns=[0],
            auto_size_columns=True,
            theme="balham",
        )

        if self.grid:
            # Refresh existing grid
            self.grid.set_lod(rows)
            self.grid.update()
        else:
            self.grid = ListOfDictsGrid(lod=rows, config=config)

    async def check_all(self):
        """
        Check reachability of all links in the grid with progress bar.
        """
        if not self.grid:
            return

        total = len(self.grid.lod or [])
        if total == 0:
            return

        # progress bar setup
        if self.progress_bar is None:
            self.progress_bar = NiceguiProgressbar(
                total=total, desc="Checking", unit="link"
            )
        else:
            self.progress_bar.total = total
            self.progress_bar.reset()
        self.progress_bar.progress.visible = True

        ui.notify("Checking example links...")

        processed = 0
        rows = self.grid.lod
        for row in rows:
            url = row.get("raw_link")
            if not url:
                processed += 1
                self.progress_bar.update(1)
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
                    row["live_status"] = error_msg or (
                        f"Error {status_code}" if status_code else "Offline"
                    )
                    row["color"] = self.COLORS["error"]
            except Exception as ex:
                row["latency"] = 0.0
                row["live_status"] = f"Ex: {ex}"
                row["color"] = self.COLORS["error"]

            processed += 1
            self.progress_bar.update(1)

        self.grid.update()
        self.progress_bar.progress.visible = False
        ui.notify("Example checks complete.")

    def setup_ui(self):
        """
        Setup grid with Google Sheet data.
        """
        with ui.row().classes("w-full items-center mb-3"):
            ui.button(
                "Reload Sheet",
                icon="cloud_download",
                on_click=lambda: background_tasks.create(self.reload_sheet_async()),
            )
            ui.button(
                "Check all",
                icon="refresh",
                on_click=lambda: background_tasks.create(self.check_all()),
            )
            ui.link(
                "Source Sheet",
                f"{self.sheet.sheet_url}",
                new_tab=True,
            ).classes("text-sm text-blue-500")
            # progress bar placeholder
            self.progress_bar = NiceguiProgressbar(
                total=1, desc="Checking", unit="link"
            )
            self.progress_bar.progress.visible = False
            self.setup_legend()

        self.build_or_refresh_grid()
        ui.timer(1.0, lambda: background_tasks.create(self.check_all()), once=True)
