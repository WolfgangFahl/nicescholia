"""
Created on 2025-12-19

@author: wf
"""

from dataclasses import field
from pathlib import Path
from typing import Dict, Optional

from basemkit.yamlable import lod_storable
import requests


@lod_storable
class Backend:
    url: str
    # Fields populated from /backend endpoint
    sparql_endpoint: Optional[str] = None
    sparql_endpoint_name: Optional[str] = None
    sparql_editurl: Optional[str] = None
    sparql_embedurl: Optional[str] = None
    text_to_topic_q_text_enabled: Optional[bool] = None
    third_parties_enabled: Optional[bool] = None
    version: Optional[str] = None


    def fetch_config(self, timeout: float = 2.0) -> bool:
        """
        Fetches the configuration JSON from the backend's /backend endpoint
        and updates the instance fields.

        Args:
            timeout (float): Request timeout in seconds.

        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure url ends with slash for clean joining, but remove it for the check
        base_url = self.url.rstrip("/")
        config_url = f"{base_url}/backend"

        try:
            headers = {"Accept": "application/json"}
            response = requests.get(config_url, headers=headers, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                self.sparql_endpoint = data.get("sparql_endpoint")
                self.sparql_endpoint_name = data.get("sparql_endpoint_name")
                self.sparql_editurl = data.get("sparql_editurl")
                self.sparql_embedurl = data.get("sparql_embedurl")
                self.text_to_topic_q_text_enabled = data.get("text_to_topic_q_text_enabled")
                self.third_parties_enabled = data.get("third_parties_enabled")
                self.version = data.get("version")
                return True
            else:
                return False
        except Exception as _e:
            # In a real app, you might want to log the error: print(f"Error fetching {config_url}: {_e}")
            return False

@lod_storable
class Backends:
    """
    Manages a collection of Scholia mirror backends
    """

    backends: Dict[str, Backend]=field(default_factory=dict)

    @classmethod
    def yaml_path(cls) -> str:
        yaml_path = Path(__file__).parent.parent / "nscholia_examples" / "backends.yaml"
        return yaml_path

    @classmethod
    def from_yaml_path(cls, yaml_path: str=None):
        if yaml_path is None:
            yaml_path = cls.yaml_path()
        backends = cls.load_from_yaml_file(yaml_path)
        return backends
