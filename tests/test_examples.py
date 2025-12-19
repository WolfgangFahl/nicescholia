"""
Created on 2025-12-19

@author: wf
"""

import asyncio
import socket

import pandas as pd
from basemkit.basetest import Basetest

from nscholia.google_sheet import GoogleSheet
from nscholia.monitor import Monitor


class TestExamples(Basetest):
    """
    Test scholia examples

    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.sheet = GoogleSheet(
            sheet_id="1cbEY7P9U-1xtvEgeAiizjJiOkpuihRFdc03JL239Ixg"
        )

    def test_dns(self):
        """
        test the assumption we have a DNS issue
        """
        hostname = "qlever.scholia.wiki"

        try:
            # Try getting address info
            print("DNS Info:", socket.getaddrinfo(hostname, 443))
        except socket.gaierror as e:
            print(f"DNS Resolution Failed: {e}")

    def testMonitor(self):
        """
        Test the monitor on a specific problematic URLs to diagnose status code 0 errors.
        """
        base_url = "https://qlever.scholia.wiki"
        for postfix in ["", "/author"]:
            url = f"{base_url}{postfix}"
            # Monitor.check is async, so we need an event loop to run it in a test
            result = asyncio.run(Monitor.check(url, timeout=5.0))

            if self.debug:
                print(f"\nChecking: {url}")
                print(f"Is Online: {result.is_online}")
                print(f"Status Code: {result.status_code}")
                print(f"Latency: {result.latency:.4f}s")
                print(f"Error: {result.error}")

    def testScholiaExamples(self):
        """
        test reading scholia examples from spreadsheet
        """
        examples = self.sheet.as_lod()

        if self.debug:
            print(f"\nFound {len(examples)} examples")
            print(f"\nFirst example:")
            for key, value in examples[0].items():
                print(f"  {key}: {value}")

        self.assertIsNotNone(examples)
        self.assertGreater(len(examples), 0)

        # Filter valid scholia links
        scholia_links = [
            ex
            for ex in examples
            if "link" in ex
            and pd.notna(ex["link"])
            and "qlever.scholia.wiki" in str(ex["link"])
        ]

        if self.debug:
            print(f"\nScholia links: {len(scholia_links)}")
            for i, example in enumerate(scholia_links[:5], 1):
                print(f"{i}. {example['link']}")

        self.assertGreater(len(scholia_links), 100)
