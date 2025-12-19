"""
Created on 2025-12-19

@author: wf
WF 2025-12-18 using Gemini Pro, Grok4, ChatGPT5 and Claude 4.5
see our more elaborate pyGenericSpreadSheet
"""

import pandas as pd


class GoogleSheet:
    """
    A simple adapter for reading data from a Google Sheet.
    """

    def __init__(self, sheet_id: str, gid: int = 0):
        """
        Initialize the GoogleSheet with the given sheet ID and optional GID.

        Args:
            sheet_id (str): The ID of the Google Sheet.
            gid (int): The sheet tab ID (default is 0).
        """
        self.base_url = "https://docs.google.com/spreadsheets"
        self.sheet_id = sheet_id
        self.gid = gid
        self.lod = None
        self.sheet_url = f"{self.base_url}/d/{self.sheet_id}"
        self.export_url = f"{self.sheet_url}/export?format=csv&gid={self.gid}"

    def as_lod(self) -> list[dict]:
        """
        Fetch the sheet data as a list of dictionaries (LOD).

        replaces NaNs with empty strings to avoid "NaN horror" in downstream usage.

        Returns:
            list[dict]: The rows from the sheet as a list of dictionaries.
        """
        df = pd.read_csv(self.export_url)

        # Fix NaN horror: replace all NaN/None values with empty strings
        # This prevents float('nan') from crashing UI logic or showing up as text-NaN
        df = df.fillna("")

        self.lod = df.to_dict("records")
        return self.lod
