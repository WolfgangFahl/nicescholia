"""
generic Dashboard
"""

from nicegui import ui


class Dashboard:
    """
    UI for monitoring a list of item using ListOfDictsGrid.
    """

    # Color constants for different states
    COLORS = {
        "checking": "#f0f0f0",  # Light gray
        "success": "#d1fae5",  # Light green - endpoint online and update query works
        "warning": "#fef3c7",  # Light yellow - endpoint online but update query fails
        "error": "#fee2e2",  # Light red - endpoint offline/unreachable
    }

    def __init__(self, solution):
        self.solution = solution
        self.webserver = solution.webserver
        self.legend_row = None
        self.grid = None  # Will hold the ListOfDictsGrid instance

    def setup_legend(self):
        # Add legend
        with ui.row().classes("ml-auto gap-4") as self.legend_row:
            ui.label("🟢 Success").classes("text-sm")
            ui.label("🟡 Warning").classes("text-sm")
            ui.label("🔴 Error").classes("text-sm")

    def setup_ui(self):
        """
        Base setup method to be overridden by subclasses
        """
        pass

    async def check_all(self):
        """
        Base check method to be overridden by subclasses
        """
        pass
