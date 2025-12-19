"""
Created on 2025-12-19

@author: wf
"""


from pathlib import Path

from basemkit.basetest import Basetest
from nscholia.backend import Backends


class TestBackends(Basetest):
    """
    Test reading the Scholia mirror network backends configuration
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def test_read_backends(self):
        """
        Test reading the endpoints from the YAML file
        """
        backends=Backends.from_yaml_path()
        if self.debug:
            print(f"Loaded {len(backends.backends)} backends.")
        for name,backend in backends.backends.items():
            backend.fetch_config()
            if self.debug:
                print(f"{name}:{backend}")



