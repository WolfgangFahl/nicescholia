"""
Availability monitoring logic
"""

import time
from dataclasses import dataclass

import httpx


@dataclass
class StatusResult:
    endpoint_name: str
    url: str
    status_code: int = 0
    latency: float = 0.0
    error: str = ""

    @property
    def is_online(self) -> bool:
        # 2xx success, 3xx redirects (common for shortlinks) are considered OK
        return 200 <= self.status_code < 400


class Monitor:
    """
    Checks endpoint availability
    """

    @staticmethod
    async def check(url: str, timeout: float = 5.0) -> StatusResult:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=timeout)
                duration = time.time() - start_time
                return StatusResult(
                    endpoint_name="",  # Filled by caller
                    url=url,
                    status_code=response.status_code,
                    latency=round(duration, 3),
                )
        except httpx.TimeoutException:
            return StatusResult(endpoint_name="", url=url, error="Timeout")
        except Exception as e:
            return StatusResult(endpoint_name="", url=url, error=str(e))
