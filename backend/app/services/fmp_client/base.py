"""
PATH: backend/app/services/fmp_client/base.py
PURPOSE: FMP API base client with connection management and retry logic
WHY: Isolates transport concerns (HTTP, auth, retries) from business methods
FLOW:
  ┌───────────┐    ┌──────────┐    ┌──────────────┐
  │ endpoint  │ →  │ _get()   │ →  │ JSON data    │
  └───────────┘    └──────────┘    └──────────────┘
DEPENDENCIES:
  - aiohttp: async HTTP client
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# FMP API Configuration
FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
# Stay under plan budget (~5–10 req/s peak). Default: ~0.8 req/s to avoid 429 storms.
FMP_MIN_INTERVAL_SEC = float(os.environ.get("FMP_MIN_INTERVAL_SEC", "1.25"))


class FMPClientBase:
    """
    Base async client for Financial Modeling Prep API.
    
    Provides connection management and a _get() helper with
    retry logic, rate-limit handling, and error recovery.
    """

    _last_request_mono: float = 0.0
    _rate_lock: Optional[asyncio.Lock] = None
    
    def __init__(self, api_key: Optional[str] = None, min_interval_sec: Optional[float] = None):
        """
        Initialize FMP client.
        
        Args:
            api_key: FMP API key. Falls back to FMP_API_KEY env var.
            min_interval_sec: Minimum seconds between requests (global throttle).
        """
        self.api_key = api_key or FMP_API_KEY
        if not self.api_key:
            raise ValueError("FMP API key required. Set FMP_API_KEY env var.")
        
        self.base_url = FMP_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.min_interval_sec = (
            FMP_MIN_INTERVAL_SEC if min_interval_sec is None else float(min_interval_sec)
        )
        if FMPClientBase._rate_lock is None:
            FMPClientBase._rate_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _throttle(self) -> None:
        """Pace requests so we stay within FMP limits instead of retrying 429s."""
        lock = FMPClientBase._rate_lock
        if lock is None:
            FMPClientBase._rate_lock = asyncio.Lock()
            lock = FMPClientBase._rate_lock
        async with lock:
            now = asyncio.get_event_loop().time()
            wait = self.min_interval_sec - (now - FMPClientBase._last_request_mono)
            if wait > 0:
                await asyncio.sleep(wait)
            FMPClientBase._last_request_mono = asyncio.get_event_loop().time()
    
    async def _get(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Any:
        """
        Make GET request to FMP API with retry logic.
        
        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            retries: Number of retries for rate limits.
            
        Returns:
            JSON response data.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key
        
        for attempt in range(retries):
            try:
                await self._throttle()
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Still hit the ceiling — back off, then fail soft
                        wait_time = min(15 + attempt * 15, 60)
                        logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 402:
                        # Payment required - don't retry
                        logger.debug(f"402 Payment required for {endpoint}")
                        return None
                    else:
                        logger.error(f"FMP API error: {response.status} for {endpoint}")
                        return None
            except Exception as e:
                logger.error(f"FMP request failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
