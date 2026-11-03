"""Base models and interface for product data extractors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import logging

from curl_cffi import requests

logger = logging.getLogger("pricepulse.extractors")


@dataclass
class ProductData:
    name: str
    price: Decimal
    currency: Optional[str]
    in_stock: bool
    url: str
    image_url: Optional[str] = None


class BaseExtractor(ABC):
    """Abstract base class that all extractors implement."""

    @abstractmethod
    def extract(self, html: str, url: str) -> Optional[ProductData]:
        """Extract structured product information from raw HTML."""
        pass


def fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch web page HTML with browser impersonation to bypass basic anti-bot blocks."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        session = requests.Session(impersonate="chrome124")
        response = session.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.text
        logger.warning("Failed to fetch %s (HTTP %s)", url, response.status_code)
        return None
    except Exception as e:
        logger.error("Network error while fetching %s: %s", url, str(e))
        return None
