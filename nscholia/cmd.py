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
        parser = super().getArgParser(description, version_msg)
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
