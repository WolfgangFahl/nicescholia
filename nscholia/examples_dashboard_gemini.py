import asyncio
from typing import Dict

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from nicegui import ui, run
from nscholia.dashboard import Dashboard
from nscholia.monitor import Monitor, StatusResult

from nscholia.google_sheet import GoogleSheet


class ExampleDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Examples from a Google Sheet.
    Includes background loading, progress tracking, and separate reload capabilities.
    """

    def __init__(self, solution, sheet: GoogleSheet):
        super().__init__(solution)
        self.webserver = solution.webserver
        self.progress_bar = None
        self.grid_container = None
        self.sheet = sheet
        self.grid = None
        self.timeout_seconds = 5.0

        self.COLORS.update({"pending": "#ffffff", "checking": "#f0f0f0"})

    def setup_ui(self):
        """Setup the Dashboard UI elements."""
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Scholia Examples").classes("text-2xl font-bold")

            with ui.row().classes("gap-2"):
                ui.button("Reload Sheet", icon="refresh", on_click=self.reload_sheet).props("outline")
                ui.button("Check Links", icon="network_check", on_click=self.check_all)

                ui.link(
                    "Source Sheet",
                    f"{self.sheet.sheet_url}",
                    new_tab=True,
                ).classes("text-sm text-blue-500 self-center ml-2")

            self.setup_legend()
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.icon("timer")
            timeout_slider = ui.slider(min=1, max=60, step=0.5, value=self.timeout_seconds).classes("w-64")
            ui.label().bind_text_from(timeout_slider, "value", lambda v: f"Timeout: {float(v):.1f} s")
            timeout_slider.bind_value(self, "timeout_seconds")


        self.progress_bar = NiceguiProgressbar(total=100, desc="Status", unit="%")
        self.progress_bar.progress.visible = False

        self.grid_container = ui.column().classes("w-full h-full")

        # Trigger load in background
        ui.timer(0.1, self.reload_sheet, once=True)

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
            # Simple string check now works because fillna("") guaranteed strings
            link_url = item.get("link", "") # Default to empty string if column missing

            if not link_url or not link_url.startswith("http"):
                continue

            link_html = Link.create(link_url, link_url)

            rows.append(
                {
                    "raw_link": link_url,
                    "link_col": link_html,

                    # Direct .get() is now safe. No more get_val helper.
                    "comment": item.get("comment", ""),
                    "sheet_status": item.get("status", "-"), # Default to "-" if empty
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
            # Kept the colon fix from before
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

    def set_result(self,row:Dict[str,str],result:StatusResult,ex:Exception=None):
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
        """
        check a single row
        """
        url = row.get("raw_link")
        if not url:
            return
        try:
            row["live_status"] = "Checking..."
            result = await Monitor.check(url,timeout=self.timeout_seconds)
            self.set_result(row, result)
        except Exception as ex:
            self.set_result(None,ex)
