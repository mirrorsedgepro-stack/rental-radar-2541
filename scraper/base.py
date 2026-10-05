"""
Base Portal Scraper Architecture
Provides resilient HTTP networking, realistic browser fingerprint headers,
exponential backoff retry policies, and rate-limiting across all site scrapers.
"""

import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import CanonicalListing

logger = logging.getLogger(__name__)

# Realistic Australian browser User-Agents
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    # Mobile iOS Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

class BasePortalScraper(ABC):
    """
    Abstract Base Class for Australian Real Estate Portal Scrapers.
    Subclasses implement site-specific extraction logic.
    """

    PORTAL_NAME = "Base"
    BASE_URL = ""

    def __init__(
        self,
        request_delay: float = 1.0,
        max_retries: int = 3,
        proxy_url: Optional[str] = None
    ):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.proxy_url = proxy_url
        self.session = requests.Session()
        if self.proxy_url:
            self.session.proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url
            }

    def get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generates realistic browser headers tailored to Australian requests."""
        ua = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def safe_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15
    ) -> Optional[requests.Response]:
        """
        Executes an HTTP GET request with jittered rate-limiting and exponential backoff retry.
        """
        req_headers = self.get_headers(headers)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Polite rate limiting jitter (e.g. 0.8s - 1.6s)
                time.sleep(self.request_delay + random.uniform(0.1, 0.6))
                
                logger.info(f"[{self.PORTAL_NAME}] Requesting ({attempt}/{self.max_retries}): {url}")
                resp = self.session.get(url, params=params, headers=req_headers, timeout=timeout)
                
                # Check status
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (429, 503):
                    backoff = (2 ** attempt) + random.uniform(1.0, 3.0)
                    logger.warning(f"[{self.PORTAL_NAME}] Rate limited (HTTP {resp.status_code}). Backing off for {backoff:.1f}s...")
                    time.sleep(backoff)
                elif resp.status_code in (403, 404):
                    logger.warning(f"[{self.PORTAL_NAME}] Request failed with HTTP {resp.status_code}: {url}")
                    return None
                else:
                    logger.warning(f"[{self.PORTAL_NAME}] HTTP {resp.status_code} received from {url}")

            except requests.RequestException as e:
                logger.error(f"[{self.PORTAL_NAME}] Network error on attempt {attempt}: {e}")
                time.sleep(2.0 * attempt)

        logger.error(f"[{self.PORTAL_NAME}] Failed to fetch {url} after {self.max_retries} attempts.")
        return None

    @abstractmethod
    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """
        Subclasses implement this method to scrape and return a list of CanonicalListing objects.
        """
        pass
