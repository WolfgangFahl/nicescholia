'''
Created on 2025-12-19

@author: wf
'''
import pandas as pd
from basemkit.basetest import Basetest
from nscholia.google_sheet import GoogleSheet

class TestExamples(Basetest):
    """
    Test scholia examples

    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.sheet=GoogleSheet(sheet_id="1cbEY7P9U-1xtvEgeAiizjJiOkpuihRFdc03JL239Ixg")

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
            ex for ex in examples
            if 'link' in ex
            and pd.notna(ex['link'])
            and 'qlever.scholia.wiki' in str(ex['link'])
        ]

        if self.debug:
            print(f"\nScholia links: {len(scholia_links)}")
            for i, example in enumerate(scholia_links[:5], 1):
                print(f"{i}. {example['link']}")

        self.assertGreater(len(scholia_links), 100)