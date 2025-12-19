"""
Availability monitoring logic
WF 2025-12-18 using Gemini Pro, Grok4, ChatGPT5 and Claude 4.5
"""

import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class StatusResult:
    endpoint_name: str
    url: str
    status_code: int = 0
    latency: float = 0.0
    error: str = ""
    response: Optional[httpx.Response] = None

    @property
    def is_online(self) -> bool:
        # 2xx success, 3xx redirects (common for shortlinks) are considered OK
        online = 200 <= self.status_code < 400
        return online


class Monitor:
    """
    Checks endpoint availability
    """

    # Default User-Agent to avoid being blocked by servers
    DEFAULT_USER_AGENT = (
        "nscholia-monitor/1.0 (https://github.com/WolfgangFahl/nscholia)"
    )

    @staticmethod
    async def check(
        url: str, timeout: float = 5.0, user_agent: str = None
    ) -> StatusResult:
        """
        Check if an endpoint is available.

        Args:
            url: URL to check
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        if user_agent is None:
            user_agent = Monitor.DEFAULT_USER_AGENT

        headers = {"User-Agent": user_agent}
        start_time = time.time()

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers, timeout=timeout)
                duration = time.time() - start_time
                status_result = StatusResult(
                    endpoint_name="",  # Filled by caller
                    url=url,
                    status_code=response.status_code,
                    latency=round(duration, 3),
                    response=response,
                )
        except httpx.TimeoutException:
            status_result = StatusResult(endpoint_name="", url=url, error="Timeout")
        except Exception as e:
            status_result = StatusResult(endpoint_name="", url=url, error=str(e))
        return status_result
