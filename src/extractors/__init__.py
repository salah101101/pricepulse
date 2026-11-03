"""Extractor registry and dispatch."""

from urllib.parse import urlparse
from src.extractors.base import BaseExtractor, ProductData, fetch_page
from src.extractors.metadata import MetadataExtractor
from src.extractors.amazon import AmazonExtractor


def get_extractor(url: str) -> BaseExtractor:
    """Route URL to the most suitable extractor based on domain name."""
    domain = urlparse(url).netloc.lower()

    if "amazon." in domain:
        return AmazonExtractor()

    # Universal metadata extractor handles all standard stores
    return MetadataExtractor()


__all__ = ["BaseExtractor", "ProductData", "fetch_page", "get_extractor"]
