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
        # Default to None so Backends uses its internal default path
        self.yaml_path = yaml_path
        self.backends_config = None
        self.progress_bar = None
        self.grid_container = None
        self.grid = None
        self.timeout_seconds = 2.0

        # extend colors if needed
        self.COLORS.update({
            "pending": "#ffffff",
            "checking": "#f0f0f0",
            "offline": "#ffcccc" # Light red for connect failures
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

        # Trigger load in background
        ui.timer(0.1, self.reload_config, once=True)

    async def reload_config(self):
        """Reload data from the YAML file."""
        self.progress_bar.progress.visible = True
        self.progress_bar.set_description("Loading YAML Config...")
        self.progress_bar.update(0)

        try:
            # CORRECTED: Use the class method provided in your snippet
            # IO bound loading of YAML
            self.backends_config = await run.io_bound(Backends.from_yaml_path, self.yaml_path)

            self.render_grid()
            if self.backends_config and self.backends_config.backends:
                ui.notify(f"Successfully loaded {len(self.backends_config.backends)} backends")
            else:
                ui.notify("Loaded empty configuration", type="warning")

        except Exception as e:
            ui.notify(f"Error loading backends: {str(e)}", type="negative")
            if self.solution:
                self.solution.handle_exception(e)
        finally:
            self.progress_bar.progress.visible = False

    def render_grid(self):
        """Transform backend objects to LOD and render AG Grid."""
        self.grid_container.clear()

        rows = []
        # The lod_storable structure usually results in a dict for backends
        if self.backends_config and self.backends_config.backends:
            for key, backend in self.backends_config.backends.items():
                link_html = Link.create(backend.url, "Visit")

                rows.append({
                    "key": key,
                    "url": backend.url, # raw url for logic
                    "link_col": link_html,
                    "version": backend.version or "-",
                    "sparql": backend.sparql_endpoint or "-",
                    "status_msg": "Pending",
                    "color": self.COLORS["pending"],
                    # Hidden reference to the actual backend object for updates
                    "_backend_obj": backend
                })

        column_defs = [
            {"headerName": "ID", "field": "key", "width": 150, "pinned": "left"},
            {"headerName": "Link", "field": "link_col", "width": 80},
            {"headerName": "Live Status", "field": "status_msg", "width": 180},
            {"headerName": "Version", "field": "version", "width": 200},
            {
                "headerName": "SPARQL Endpoint",
                "field": "sparql",
                "width": 300,
                "tooltipField": "sparql"
            },
            {
                "headerName": "Base URL",
                "field": "url",
                "width": 250,
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
            html_columns=[1], # link_col
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

        # Reset visual status
        for row in rows:
            row["status_msg"] = "Queued..."
            row["color"] = self.COLORS["checking"]
        self.grid.update()

        # Process in batches to avoid choking the IO
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
        """
        Check a single backend row.
        """
        backend_obj = row.get("_backend_obj")
        if not backend_obj:
            return

        try:
            row["status_msg"] = "Checking..."

            # Run the synchronous fetch_config call in a thread
            success = await run.io_bound(backend_obj.fetch_config, self.timeout_seconds)

            if success:
                row["status_msg"] = "OK"
                row["color"] = self.COLORS["success"]
                # Update cols with data fetched into the object
                row["version"] = backend_obj.version or "?"
                row["sparql"] = backend_obj.sparql_endpoint or "?"
            else:
                row["status_msg"] = "Unreachable / No JSON"
                row["color"] = self.COLORS["offline"]

        except Exception as ex:
            row["status_msg"] = f"Error: {str(ex)}"
            row["color"] = self.COLORS["error"]