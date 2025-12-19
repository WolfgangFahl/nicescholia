"""
Examples Dashboard

WF 2025-12-18 using Gemini Pro, Grok4, ChatGPT5 and Claude 4.5 - GeminiPro clearly>
winning the contest

"""

import asyncio
from typing import Dict

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from nicegui import run, ui

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor, StatusResult


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet.
    Includes background loading, progress tracking, and separate reload capabilities.
    """

    DEFAULT_URL_BASE = "https://qlever.scholia.wiki"

    def __init__(self, solution, sheet: GoogleSheet):
        super().__init__(solution)
        self.webserver = solution.webserver
        self.progress_bar = None
        self.grid_container = None
        self.sheet = sheet
        self.grid = None
        self.timeout_seconds = 5.0
        self.selected_backend_name = "qlever-scholia"

        self.COLORS.update({"pending": "#ffffff", "checking": "#f0f0f0"})

    def setup_ui(self):
        """Setup the Dashboard UI elements."""
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Scholia Examples").classes("text-2xl font-bold")

            backend_names = list(self.webserver.backends.backends.keys()) if self.webserver.backends else []

            self.backend_select = ui.select(
                options=backend_names,
                label="Backend"
            ).classes("w-48").bind_value(self, "selected_backend_name").on_value_change(lambda: self.render_grid())

            with ui.row().classes("gap-2"):
                ui.button(
                    "Reload Sheet", icon="refresh", on_click=self.reload_sheet
                ).props("outline")
                ui.button("Check Links", icon="network_check", on_click=self.check_all)

                ui.link(
                    "Source Sheet",
                    f"{self.sheet.sheet_url}",
                    new_tab=True,
                ).classes("text-sm text-blue-500 self-center ml-2")

            self.setup_legend()
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.icon("timer")
            timeout_slider = ui.slider(
                min=1, max=60, step=0.5, value=self.timeout_seconds
            ).classes("w-64")
            ui.label().bind_text_from(
                timeout_slider, "value", lambda v: f"Timeout: {float(v):.1f} s"
            )
            timeout_slider.bind_value(self, "timeout_seconds")

        self.progress_bar = NiceguiProgressbar(total=100, desc="Status", unit="%")
        self.progress_bar.progress.visible = False

        self.grid_container = ui.column().classes("w-full h-full")

        # Trigger load in background
        ui.timer(0.1, self.reload_sheet, once=True)

    def get_target_url(self, original_url: str) -> str:
        """Transforms the original URL based on the selected backend."""
        if not original_url:
            return ""

        if not self.selected_backend_name or not self.webserver.backends:
            return original_url

        target_backend = self.webserver.backends.backends.get(self.selected_backend_name)

        if target_backend and original_url.startswith(self.DEFAULT_URL_BASE):
            return original_url.replace(self.DEFAULT_URL_BASE, target_backend.url)

        return original_url

    async def reload_sheet(self):
        """Reload data from the Google Sheet in the background."""
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description("Loading Sheet Data...")
        self.progress_bar.update(0)

        try:
            if self.sheet:
                # NaNs are now handled inside as_lod via fillna("")
                await run.io_bound(self.sheet.as_lod)

                self.render_grid()
                ui.notify(f"Successfully loaded {len(self.sheet.lod)} examples")
            else:
                ui.notify("Sheet configuration missing", type="negative")

        except Exception as e:
            ui.notify(f"Error loading sheet: {str(e)}", type="negative")
            self.solution.handle_exception(e)
        finally:
            self.progress_bar.progress.visible = False

    def render_grid(self):
        """Transform raw data and render the AG Grid."""
        self.grid_container.clear()

        rows = []
        data_source = self.sheet.lod if self.sheet.lod else []

        for item in data_source:
            sheet_url = item.get("link", "")

            if not sheet_url or not sheet_url.startswith("http"):
                continue

            effective_url = self.get_target_url(sheet_url)
            link_html = Link.create(effective_url, "View")

            rows.append(
                {
                    "raw_link": effective_url,
                    "original_link": sheet_url,
                    "link_col": link_html,
                    "comment": item.get("comment", ""),
                    "sheet_status": item.get("status", "-"),
                    "pr": item.get("PR", ""),
                    "github1": item.get("GitHub ticket 1", ""),
                    "error1": item.get("error message 1", ""),
                    "live_status": "Pending",
                    "latency": 0.0,
                    "color": self.COLORS["pending"],
                }
            )

        column_defs = [
            {"headerName": "Link", "field": "link_col", "width": 70},
            {
                "headerName": "Url",
                "field": "raw_link",
                "width": 300,
                "cellStyle": {
                    "textOverflow": "ellipsis",
                    "overflow": "hidden",
                    "whiteSpace": "nowrap",
                },
                "tooltipField": "raw_link",
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
                ":valueFormatter": "params.value ? params.value.toFixed(3) : ''",
            },
        ]

        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            ":getRowStyle": """function(params) { return { background: params.data.color }; }""",
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
        """Check all links in the grid asynchronously."""
        if not self.grid:
            ui.notify("No data loaded to check")
            return

        rows = self.grid.lod
        total = len(rows)

        self.progress_bar.total = total
        self.progress_bar.value = 0
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description(f"Checking {total} links...")

        for row in rows:
            row["live_status"] = "Queued..."
            row["color"] = self.COLORS["checking"]
        self.grid.update()

        batch_size = 10
        for i in range(0, total, batch_size):
            batch_rows = rows[i : i + batch_size]
            tasks = [self.check_single_row(row) for row in batch_rows]
            await asyncio.gather(*tasks)
            self.progress_bar.update(len(batch_rows))
            self.grid.update()

        self.progress_bar.progress.visible = False
        ui.notify("Link checking complete")

    def set_result(
        self, row: Dict[str, str], result: StatusResult, ex: Exception = None
    ):
        if ex is not None:
            row["live_status"] = "Exception"
            row["latency"] = 0
            row["color"] = self.COLORS["error"]
        elif result.is_online:
            row["latency"] = result.latency
            row["live_status"] = f"OK ({result.status_code})"
            row["color"] = self.COLORS["success"]
        else:
            row["latency"] = 0
            error_info = result.error or f"Http {result.status_code}"
            row["live_status"] = error_info
            row["color"] = self.COLORS["error"]

    async def check_single_row(self, row: dict):
        """Check a single row"""
        url = row.get("raw_link")
        if not url:
            return

        row["live_status"] = "Checking..."
        try:
            result = await Monitor.check(url, timeout=self.timeout_seconds)
            self.set_result(row, result)
        except Exception as ex:
            self.set_result(row, None, ex)