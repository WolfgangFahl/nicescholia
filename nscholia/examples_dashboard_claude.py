"""
Created on 2025-12-19

@author: wf
"""

import asyncio

import aiohttp
from ngwidgets.lod_grid import GridConfig, ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from nscholia.dashboard import Dashboard
from nscholia.google_sheet import GoogleSheet


class ExampleDashboard(Dashboard):
    """
    UI for monitoring Scholia examples using ListOfDictsGrid.
    """

    # Color constants for different statuses (5=best, 0=worst)
    COLORS = {
        "checking": "#f0f0f0",  # Light gray
        "5": "#d1fae5",  # Light green - all good
        "4": "#e0e7ff",  # Light blue - no obvious errors
        "3": "#fef3c7",  # Light yellow - one error
        "2": "#fed7aa",  # Light orange - two errors
        "1": "#fecaca",  # Light red - more than two errors
        "0": "#fee2e2",  # Red - page does not load
        "unknown": "#f3f4f6",  # Gray - unknown status
    }

    def __init__(self, solution):
        super().__init__(solution)
        self.sheet = GoogleSheet(
            sheet_id="1cbEY7P9U-1xtvEgeAiizjJiOkpuihRFdc03JL239Ixg"
        )

    async def check_link(self, url: str) -> tuple[bool, str]:
        """
        Check if a link is accessible.

        Args:
            url: The URL to check

        Returns:
            tuple: (is_accessible, status_message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True
                ) as response:
                    return response.status < 400, f"HTTP {response.status}"
        except asyncio.TimeoutError:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)[:50]

    async def check_all(self):
        """
        Verify all example links in the grid.
        """
        if not self.grid:
            return

        ui.notify("Verifying links...")
        rows = self.grid.lod

        for row in rows:
            link = row.get("url", "")
            if not link or not isinstance(link, str) or not link.startswith("http"):
                continue

            row["verified"] = "Checking..."
            self.grid.update()

            is_accessible, message = await self.check_link(link)
            row["verified"] = "✓ Accessible" if is_accessible else f"✗ {message}"
            self.grid.update()

        ui.notify("Verification complete")

    def setup_ui(self):
        """
        Render the examples dashboard.
        """
        with ui.row().classes("w-full items-center mb-4"):
            ui.label("Scholia Examples").classes("text-2xl font-bold")
            ui.button("Verify Links", icon="link", on_click=self.check_all)

            # Status legend
            with ui.row().classes("ml-auto gap-2 text-xs"):
                for status, label in [
                    ("5", "All good"),
                    ("4", "No errors"),
                    ("3", "One error"),
                    ("2", "Two errors"),
                    ("1", "Many errors"),
                    ("0", "Won't load"),
                ]:
                    ui.label(f"{status}={label}").style(
                        f"background: {self.COLORS[status]}; "
                        f"padding: 4px 8px; border-radius: 4px"
                    )

        # Load examples from Google Sheet
        examples = self.sheet.as_lod()

        rows = []
        for ex in examples:
            link = ex.get("link", "")

            # Skip invalid rows
            if not isinstance(link, str) or not link.startswith("http"):
                continue

            # Parse status (handle NaN)
            status = str(ex.get("status", "unknown")).strip()
            if status == "nan":
                status = "unknown"

            color = self.COLORS.get(status, self.COLORS["unknown"])

            # Extract page type from URL
            page_type = "Unknown"
            if "qlever.scholia.wiki" in link:
                parts = link.split("/")
                if len(parts) > 3:
                    page_type = parts[3]

            # Clean up fields (handle NaN)
            def clean(value):
                s = str(value) if value is not None else ""
                return "" if s == "nan" else s

            rows.append(
                {
                    "link": Link.create(link, "🔗"),
                    "url": link,
                    "page_type": page_type,
                    "status": status,
                    "comment": clean(ex.get("comment", "")),
                    "error_1": clean(ex.get("error message 1", "")),
                    "error_2": clean(ex.get("error message 2", "")),
                    "error_3": clean(ex.get("error message 3", "")),
                    "verified": "",
                    "color": color,
                }
            )

        column_defs = [
            {"headerName": "Link", "field": "link", "width": 60},
            {
                "headerName": "Page Type",
                "field": "page_type",
                "sortable": True,
                "filter": True,
                "width": 150,
            },
            {
                "headerName": "Status",
                "field": "status",
                "sortable": True,
                "width": 80,
                "type": "numericColumn",
            },
            {
                "headerName": "Comment",
                "field": "comment",
                "sortable": True,
                "filter": True,
                "flex": 2,
            },
            {
                "headerName": "Error 1",
                "field": "error_1",
                "sortable": True,
                "filter": True,
                "flex": 2,
            },
            {
                "headerName": "Error 2",
                "field": "error_2",
                "sortable": True,
                "filter": True,
                "flex": 1,
            },
            {
                "headerName": "Error 3",
                "field": "error_3",
                "sortable": True,
                "filter": True,
                "flex": 1,
            },
            {
                "headerName": "Verified",
                "field": "verified",
                "sortable": True,
                "width": 150,
            },
        ]

        grid_options = {
            "rowSelection": "single",
            "animateRows": True,
            ":getRowStyle": """(params) => {
                return { background: params.data.color };
            }""",
        }

        config = GridConfig(
            column_defs=column_defs,
            key_col="url",
            options=grid_options,
            html_columns=[0],
            auto_size_columns=True,
            theme="balham",
        )

        self.grid = ListOfDictsGrid(lod=rows, config=config)
