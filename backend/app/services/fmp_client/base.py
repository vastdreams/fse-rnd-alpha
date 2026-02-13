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


class FMPClientBase:
    """
    Base async client for Financial Modeling Prep API.
    
    Provides connection management and a _get() helper with
    retry logic, rate-limit handling, and error recovery.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FMP client.
        
        Args:
            api_key: FMP API key. Falls back to FMP_API_KEY env var.
        """
        self.api_key = api_key or FMP_API_KEY
        if not self.api_key:
            raise ValueError("FMP API key required. Set FMP_API_KEY env var.")
        
        self.base_url = FMP_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
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
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
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
