"""
Created on 2025-12-19

@author: wf
"""
import asyncio

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.progress import NiceguiProgressbar
from ngwidgets.widgets import Link
from nicegui import run, ui

from nscholia.backend import Backends
from nscholia.dashboard import Dashboard


class BackendDashboard(Dashboard):
    """
    Dashboard for monitoring Scholia Backends defined in backends.yaml.
    """

    def __init__(self, solution, yaml_path: str = None):
        super().__init__(solution)
        self.webserver = solution.webserver
        self.yaml_path = yaml_path
        self.backends_config = None
        self.progress_bar = None
        self.grid_container = None
        self.grid = None
        self.timeout_seconds = 2.0

        self.COLORS.update({
            "pending": "#ffffff",
            "checking": "#f0f0f0",
            "offline": "#ffcccc"
        })

    def setup_ui(self):
        """Setup the Dashboard UI elements."""
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Scholia Backends").classes("text-2xl font-bold")

            with ui.row().classes("gap-2"):
                ui.button(
                    "Reload Config", icon="refresh", on_click=self.reload_config
                ).props("outline")
                ui.button("Check Status", icon="network_check", on_click=self.check_all)

            self.setup_legend()

        with ui.row().classes("items-center gap-3 mb-2"):
            ui.icon("timer")
            timeout_slider = ui.slider(
                min=0.5, max=10, step=0.5, value=self.timeout_seconds
            ).classes("w-64")
            ui.label().bind_text_from(
                timeout_slider, "value", lambda v: f"Timeout: {float(v):.1f} s"
            )
            timeout_slider.bind_value(self, "timeout_seconds")

        self.progress_bar = NiceguiProgressbar(total=100, desc="Status", unit="%")
        self.progress_bar.progress.visible = False

        self.grid_container = ui.column().classes("w-full h-full")

        ui.timer(0.1, self.reload_config, once=True)

    async def reload_config(self):
        """Reload data from the YAML file."""
        try:
            self.backends_config = await run.io_bound(Backends.from_yaml_path, self.yaml_path)

            self.render_grid()
            if self.backends_config and self.backends_config.backends:
                ui.notify(f"Loaded {len(self.backends_config.backends)} backends")
            else:
                ui.notify("Loaded empty configuration", type="warning")

        except Exception as e:
            ui.notify(f"Error loading backends: {str(e)}", type="negative")
            if self.solution:
                self.solution.handle_exception(e)

    def _get_sparql_link_html(self, backend_obj) -> str:
        """
        Helper function to generate the HTML link for the SPARQL edit URL.
        Reduces code duplication between render_grid and check_single_row.
        """
        sparql_val = getattr(backend_obj, "sparql_editurl", None)

        if sparql_val and str(sparql_val).startswith("http"):
            return Link.create(sparql_val, "Query")

        if sparql_val:
            return sparql_val

        return "-"

    def render_grid(self):
        """Transform backend objects to LOD and render AG Grid."""
        self.grid_container.clear()

        rows = []
        if self.backends_config and self.backends_config.backends:
            for key, backend in self.backends_config.backends.items():

                url_html = Link.create(backend.url, backend.url)
                link_html = Link.create(backend.url, "Visit")
                sparql_html = self._get_sparql_link_html(backend)

                rows.append({
                    "key": key,
                    "url_html": url_html,
                    "link_col": link_html,
                    "version": backend.version or "-",
                    "sparql_link": sparql_html,
                    "status_msg": "Pending",
                    "color": self.COLORS["pending"],
                })

        column_defs = [
            {"headerName": "ID", "field": "key", "width": 150, "pinned": "left"},
            {"headerName": "Link", "field": "link_col", "width": 80},
            {"headerName": "Live Status", "field": "status_msg", "width": 180},
            {"headerName": "Version", "field": "version", "width": 200},
            {
                "headerName": "SPARQL Endpoint",
                "field": "sparql_link",
                "width": 100
            },
            {
                "headerName": "Base URL",
                "field": "url_html",
                "width": 300,
                "cellStyle": {
                    "textOverflow": "ellipsis",
                    "overflow": "hidden",
                    "whiteSpace": "nowrap",
                },
            }
        ]

        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            ":getRowStyle": """function(params) { return { background: params.data.color }; }""",
        }

        config = GridConfig(
            column_defs=column_defs,
            key_col="key",
            options=grid_options,
            html_columns=[1, 4, 5],
            auto_size_columns=True,
            theme="balham",
        )

        with self.grid_container:
            self.grid = ListOfDictsGrid(lod=rows, config=config)

    async def check_all(self):
        """Check all backends asynchronously."""
        if not self.grid:
            ui.notify("No data loaded to check")
            return

        rows = self.grid.lod
        total = len(rows)

        self.progress_bar.total = total
        self.progress_bar.value = 0
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description(f"Checking {total} backends...")

        for row in rows:
            row["status_msg"] = "Queued..."
            row["color"] = self.COLORS["checking"]
        self.grid.update()

        batch_size = 5
        for i in range(0, total, batch_size):
            batch_rows = rows[i : i + batch_size]
            tasks = [self.check_single_row(row) for row in batch_rows]
            await asyncio.gather(*tasks)
            self.progress_bar.update(len(batch_rows))
            self.grid.update()

        self.progress_bar.progress.visible = False
        ui.notify("Backend check complete")

    async def check_single_row(self, row: dict):
        """Check a single backend row."""
        key = row.get("key")
        backend_obj = self.backends_config.backends.get(key)

        if not backend_obj:
            row["status_msg"] = "Config Missing"
            row["color"] = self.COLORS["error"]
            return

        try:
            row["status_msg"] = "Checking..."
            success = await run.io_bound(backend_obj.fetch_config, self.timeout_seconds)

            if success:
                row["status_msg"] = "OK"
                row["color"] = self.COLORS["success"]
                row["version"] = backend_obj.version or "?"
                row["sparql_link"] = self._get_sparql_link_html(backend_obj)

            else:
                row["status_msg"] = "Unreachable / No JSON"
                row["color"] = self.COLORS["offline"]

        except Exception as ex:
            row["status_msg"] = f"Error: {str(ex)}"
            row["color"] = self.COLORS["error"]