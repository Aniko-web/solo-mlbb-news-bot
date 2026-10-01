import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx
from app.utils.logger import logger
from app.utils.validators import RawCollectedItem, SourceReliability
from app.config.settings import get_settings

settings = get_settings()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class SourceCollector(ABC):
    """
    Abstract Base Class for all MLBB & Esports collectors.
    Subclasses must implement the `fetch` method.
    """

    def __init__(
        self,
        name: str,
        source_type: str,
        base_url: str,
        reliability_score: int = SourceReliability.UNKNOWN_SOURCE
    ):
        self.name = name
        self.source_type = source_type
        self.base_url = base_url
        self.reliability_score = reliability_score
        self.timeout = settings.HTTP_TIMEOUT_SECONDS
        self.max_retries = settings.MAX_HTTP_RETRIES

    @abstractmethod
    async def fetch(self) -> List[RawCollectedItem]:
        """Fetch raw items from source and return structured RawCollectedItem list."""
        pass

    async def health_check(self) -> bool:
        """
        Check if the target source is reachable.
        Returns True if reachable (200..399), False otherwise.
        """
        try:
            resp = await self._get(self.base_url, timeout=10.0)
            return resp is not None and resp.status_code < 400
        except Exception as e:
            logger.warning(f"Health check failed for {self.name} ({self.base_url}): {e}")
            return False

    async def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Optional[httpx.Response]:
        """
        Perform an async HTTP GET request with retries and exponential backoff.
        """
        req_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        }
        if headers:
            req_headers.update(headers)

        req_timeout = timeout or float(self.timeout)

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=req_timeout,
                    verify=False  # Allow flexible SSL certificates for game portals
                ) as client:
                    response = await client.get(url, params=params, headers=req_headers)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"[{self.name}] HTTP error on {url} (attempt {attempt}/{self.max_retries}): {e.response.status_code}"
                )
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[{self.name}] Network error on {url} (attempt {attempt}/{self.max_retries}): {e}"
                )
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error on {url}: {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(1.5 * attempt)

        return None
