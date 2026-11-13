"""
Created on 2026-11-13

@author: wf

NiceGUI views of the Scholia aspects
see https://github.com/WolfgangFahl/nicescholia/issues/17
"""

from typing import Any, Dict, List, Optional

from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import run, ui

from nscholia.aspect import AspectQueries, AspectResult


class AspectView:
    """
    a single view of an aspect: the result of one named parameterized
    query shown by the display type of the query
    """

    WIKIDATA_ENTITY_PREFIX = "http://www.wikidata.org/entity/"
    WIKIDATA_URL = "https://www.wikidata.org/wiki/"

    def __init__(self, solution, aspect: str, view: str):
        """
        constructor

        Args:
            solution: the web solution to show the view in
            aspect: the aspect e.g. author
            view: the view e.g. list-of-publications
        """
        self.solution = solution
        self.webserver = solution.webserver
        self.aspect = aspect
        self.view = view
        self.status_label = None
        self.grid_container = None
        self.grid = None

    def setup_ui(self, pid: str, limit: Optional[int] = None):
        """
        setup the user interface and load the result in the background

        Args:
            pid: the identifier of the start node e.g. Q80
            limit: the maximum number of rows - default of the query if None
        """
        aspect_queries = self.webserver.get_aspect_queries()
        name = AspectQueries.query_name(self.aspect, self.view)
        query = aspect_queries.get_query(name)
        with ui.row().classes("w-full items-center"):
            ui.link(f"{query.title}", f"/{self.aspect}/{self.view}/{pid}").classes(
                "text-xl font-bold"
            )
            ui.link(pid, f"{self.WIKIDATA_URL}{pid}", new_tab=True)
            self.status_label = ui.label("loading ...").classes("text-sm")
        self.grid_container = ui.column().classes("w-full")

        async def load():
            await self.load(pid, limit)

        ui.timer(0.1, load, once=True)

    async def load(self, pid: str, limit: Optional[int] = None):
        """
        run the query in the background and show its result

        Args:
            pid: the identifier of the start node
            limit: the maximum number of rows
        """
        try:
            result = await run.io_bound(
                self.webserver.get_aspect_result, self.aspect, self.view, pid, limit
            )
            self.show(result)
        except Exception as ex:
            self.status_label.set_text(f"failed: {ex}")
            self.solution.handle_exception(ex)

    def entity_link(self, row: Dict[str, Any], column: str) -> str:
        """
        get the html link for the entity in the given column with the
        label of the Scholia column convention <column>Label

        Args:
            row: the result row
            column: the column with the entity url
        """
        html = ""
        url = row.get(column)
        if url:
            qid = str(url).replace(self.WIKIDATA_ENTITY_PREFIX, "")
            label = row.get(f"{column}Label") or qid
            html = Link.create(f"{self.WIKIDATA_URL}{qid}", str(label), target="_blank")
        return html

    def as_grid_rows(self, result: AspectResult) -> List[Dict[str, Any]]:
        """
        convert the result rows for display: entity columns become links
        with their label, the label and Url helper columns are dropped
        """
        grid_rows = []
        for index, row in enumerate(result.rows):
            grid_row: Dict[str, Any] = {"#": index + 1}
            for column in self.display_columns(result):
                value = row.get(column)
                if f"{column}Label" in result.columns:
                    value = self.entity_link(row, column)
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                grid_row[column] = value
            grid_rows.append(grid_row)
        return grid_rows

    def display_columns(self, result: AspectResult) -> List[str]:
        """
        get the columns to display - helper columns of the Scholia column
        convention ending with Label or Url are shown via their entity
        """
        columns = [
            column
            for column in result.columns
            if not column.endswith("Label") and not column.endswith("Url")
        ]
        return columns

    def show(self, result: AspectResult):
        """
        show the given result by its display type

        Args:
            result: the result of the query of this view
        """
        if result.endpoint_name is None:
            self.status_label.set_text(f"no endpoint answered: {result.errors}")
            return
        self.status_label.set_text(
            f"{len(result.rows)} rows from {result.endpoint_name}"
        )
        columns = self.display_columns(result)
        html_columns = [
            index + 1
            for index, column in enumerate(columns)
            if f"{column}Label" in result.columns
        ]
        column_defs = [{"headerName": "#", "field": "#", "width": 60}]
        for column in columns:
            column_defs.append(
                {
                    "headerName": column,
                    "field": column,
                    "wrapText": True,
                    "autoHeight": True,
                    "flex": 3 if column in ("work", "authors") else 1,
                }
            )
        config = GridConfig(
            column_defs=column_defs,
            key_col="#",
            html_columns=html_columns,
            auto_size_columns=False,
            theme="balham",
        )
        self.grid_container.clear()
        with self.grid_container:
            # only the Table display type is supported so far
            if result.default_view != "Table":
                ui.label(f"display type {result.default_view} shown as table")
            self.grid = ListOfDictsGrid(lod=self.as_grid_rows(result), config=config)
