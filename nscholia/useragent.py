"""
Created on 2026-09-23

@author: wf
"""

from nscholia.version import Version


def get_user_agent() -> str:
    """
    User-Agent per Wikimedia policy: client name, version and a contact URL.
    Wikimedia rejects requests without such a header with
    403 "Unauthorized User-Agent".
    """
    version = Version()
    user_agent = f"{version.name}/{version.version} (+{version.cm_url})"
    return user_agent


USER_AGENT = get_user_agent()
