"""Specialized adapter for Amazon product pages."""

import logging
from bs4 import BeautifulSoup
from typing import Optional

from src.currency import parse_price
from src.extractors.base import BaseExtractor, ProductData

logger = logging.getLogger("pricepulse.extractors.amazon")


class AmazonExtractor(BaseExtractor):
    """Parser specifically designed for Amazon DOM structure."""

    def extract(self, html: str, url: str) -> Optional[ProductData]:
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Product title
        title_elem = soup.find(id="productTitle")
        if not title_elem:
            # Check secondary title selectors
            title_elem = soup.find("h1", class_="a-size-large") or soup.find("title")

        if not title_elem:
            logger.warning("Could not find product title on Amazon page: %s", url)
            return None

        name = title_elem.get_text().strip()

        # 2. Price extraction
        price = None
        currency = None

        # Best Amazon price selectors in priority order
        price_selectors = [
            ".apexPriceToPay .a-offscreen",
            "#corePrice_feature_div .a-price .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
            "#priceblock_dealprice",
            "#priceblock_ourprice",
            "#price_inside_buybox",
            ".a-price .a-offscreen",
        ]

        for selector in price_selectors:
            elem = soup.select_one(selector)
            if elem:
                extracted_price, extracted_cur = parse_price(elem.get_text())
                if extracted_price is not None:
                    price = extracted_price
                    currency = extracted_cur
                    break

        # Fallback to whole + fraction components
        if price is None:
            whole_elem = soup.select_one(".a-price-whole")
            fraction_elem = soup.select_one(".a-price-fraction")
            symbol_elem = soup.select_one(".a-price-symbol")

            if whole_elem:
                frac = fraction_elem.get_text().strip() if fraction_elem else "00"
                combined = f"{whole_elem.get_text().strip()}.{frac}"
                price, _ = parse_price(combined)
                if symbol_elem:
                    _, currency = parse_price(symbol_elem.get_text().strip())

        if price is None:
            logger.warning("Could not locate price element on Amazon page: %s", url)
            return None

        # Fallback currency detection via symbol or domain
        if currency is None:
            symbol_elem = soup.select_one(".a-price-symbol")
            if symbol_elem:
                _, currency = parse_price(symbol_elem.get_text().strip())

        if currency is None:
            domain_url = url.lower()
            if ".co.uk" in domain_url:
                currency = "GBP"
            elif any(d in domain_url for d in [".de", ".fr", ".es", ".it"]):
                currency = "EUR"
            elif ".sa" in domain_url:
                currency = "SAR"
            elif ".ae" in domain_url:
                currency = "AED"
            elif ".ca" in domain_url:
                currency = "CAD"
            elif ".com.au" in domain_url:
                currency = "AUD"
            elif ".co.jp" in domain_url:
                currency = "JPY"
            elif "amazon.com" in domain_url:
                currency = "USD"

        # 3. Availability
        in_stock = True
        avail_elem = soup.find(id="availability")
        if avail_elem:
            text = avail_elem.get_text().lower()
            if "currently unavailable" in text or "out of stock" in text:
                in_stock = False

        # 4. Product image
        image_url = None
        img_elem = soup.find(id="landingImage") or soup.find(id="imgBlkFront")
        if img_elem:
            image_url = img_elem.get("data-old-hires") or img_elem.get("src")

        return ProductData(
            name=name,
            price=price,
            currency=currency,
            in_stock=in_stock,
            url=url,
            image_url=image_url
        )
