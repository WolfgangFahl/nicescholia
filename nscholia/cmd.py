"""
Command line entry point
"""

import sys
from argparse import ArgumentParser

from ngwidgets.cmd import WebserverCmd

from nscholia.webserver import ScholiaWebserver


class ScholiaCmd(WebserverCmd):
    """
    Command Line Interface
    """

    def getArgParser(self, description: str, version_msg) -> ArgumentParser:
        """
        get the argument parser
        """
        parser = super().getArgParser(description, version_msg)
        parser.add_argument(
            "--sheet-id",
            dest="sheet_id",
            default="1cbEY7P9U-1xtvEgeAiizjJiOkpuihRFdc03JL239Ixg",
            help="Google Sheet ID for Scholia examples (CSV export will be used)",
        )
        parser.add_argument(
            "--sheet-gid",
            dest="sheet_gid",
            type=int,
            default=0,
            help="Google Sheet GID (tab id), default: 0",
        )

        return parser


def main(argv: list = None):
    cmd = ScholiaCmd(
        config=ScholiaWebserver.get_config(),
        webserver_cls=ScholiaWebserver,
    )
    exit_code = cmd.cmd_main(argv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
