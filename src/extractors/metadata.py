"""Universal metadata extractor supporting JSON-LD, Microdata, and OpenGraph."""

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from src.currency import parse_price
from src.extractors.base import BaseExtractor, ProductData

logger = logging.getLogger("pricepulse.extractors.metadata")


class MetadataExtractor(BaseExtractor):
    """Extracts product data from standard web metadata."""

    def extract(self, html: str, url: str) -> Optional[ProductData]:
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # 1. Try JSON-LD schemas
        product = self._extract_json_ld(soup, url)
        if product:
            return product

        # 2. Try HTML Microdata
        product = self._extract_microdata(soup, url)
        if product:
            return product

        # 3. Try OpenGraph / Meta tags
        product = self._extract_meta_tags(soup, url)
        if product:
            return product

        return None

    def _extract_json_ld(self, soup: BeautifulSoup, url: str) -> Optional[ProductData]:
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            item = self._find_product_node(data)
            if not item:
                continue

            name = item.get("name")
            if isinstance(name, dict):
                name = name.get("name") or name.get("@value")
            name = str(name).strip() if name else ""

            # Extract image
            image_url = None
            raw_image = item.get("image")
            if isinstance(raw_image, list) and raw_image:
                first = raw_image[0]
                image_url = first if isinstance(first, str) else first.get("url")
            elif isinstance(raw_image, dict):
                image_url = raw_image.get("url")
            elif isinstance(raw_image, str):
                image_url = raw_image

            # Extract offers
            offers = item.get("offers")
            price, currency, in_stock = self._parse_offers(offers)

            if price is not None and name:
                return ProductData(
                    name=name,
                    price=price,
                    currency=currency,
                    in_stock=in_stock,
                    url=url,
                    image_url=image_url
                )

        return None

    def _find_product_node(self, node: Any) -> Optional[Dict[str, Any]]:
        """Recursively search for a node with @type 'Product'."""
        if isinstance(node, dict):
            type_val = node.get("@type")
            if type_val == "Product" or (isinstance(type_val, list) and "Product" in type_val):
                return node
            if "@graph" in node and isinstance(node["@graph"], list):
                for sub in node["@graph"]:
                    found = self._find_product_node(sub)
                    if found:
                        return found
            for val in node.values():
                if isinstance(val, (dict, list)):
                    found = self._find_product_node(val)
                    if found:
                        return found
        elif isinstance(node, list):
            for item in node:
                found = self._find_product_node(item)
                if found:
                    return found
        return None

    def _parse_offers(self, offers: Any) -> tuple[Optional[Decimal], Optional[str], bool]:
        """Extract price, currency, and stock status from schema.org offers."""
        if not offers:
            return None, None, True

        target_offer = None
        if isinstance(offers, list) and offers:
            target_offer = offers[0]
        elif isinstance(offers, dict):
            target_offer = offers

        if not target_offer:
            return None, None, True

        raw_price = target_offer.get("price") or target_offer.get("lowPrice")
        currency = target_offer.get("priceCurrency")
        availability = target_offer.get("availability", "")

        in_stock = "OutOfStock" not in str(availability)

        if raw_price is not None:
            price, detected_currency = parse_price(str(raw_price))
            return price, (currency or detected_currency), in_stock

        return None, None, in_stock

    def _extract_microdata(self, soup: BeautifulSoup, url: str) -> Optional[ProductData]:
        price_elem = soup.find(attrs={"itemprop": "price"})
        if not price_elem:
            return None

        raw_price = price_elem.get("content") or price_elem.get_text()
        price, detected_cur = parse_price(str(raw_price))
        if price is None:
            return None

        cur_elem = soup.find(attrs={"itemprop": "priceCurrency"})
        currency = cur_elem.get("content") or cur_elem.get_text() if cur_elem else detected_cur

        name_elem = soup.find(attrs={"itemprop": "name"})
        name = name_elem.get("content") or name_elem.get_text() if name_elem else ""

        img_elem = soup.find(attrs={"itemprop": "image"})
        image_url = img_elem.get("src") or img_elem.get("content") if img_elem else None

        avail_elem = soup.find(attrs={"itemprop": "availability"})
        avail_str = avail_elem.get("href") or avail_elem.get("content") or "" if avail_elem else ""
        in_stock = "OutOfStock" not in avail_str

        if name and price:
            return ProductData(
                name=name.strip(),
                price=price,
                currency=str(currency).strip() if currency else None,
                in_stock=in_stock,
                url=url,
                image_url=image_url
            )
        return None

    def _extract_meta_tags(self, soup: BeautifulSoup, url: str) -> Optional[ProductData]:
        price_meta = (
            soup.find("meta", property="product:price:amount") or
            soup.find("meta", property="og:price:amount") or
            soup.find("meta", attrs={"name": "twitter:data1"})
        )
        if not price_meta:
            return None

        raw_price = price_meta.get("content")
        price, detected_cur = parse_price(str(raw_price))
        if price is None:
            return None

        cur_meta = (
            soup.find("meta", property="product:price:currency") or
            soup.find("meta", property="og:price:currency")
        )
        currency = cur_meta.get("content") if cur_meta else detected_cur

        title_meta = (
            soup.find("meta", property="og:title") or
            soup.find("meta", attrs={"name": "twitter:title"}) or
            soup.find("title")
        )
        name = title_meta.get("content") if title_meta and title_meta.name == "meta" else (
            title_meta.get_text() if title_meta else ""
        )

        img_meta = soup.find("meta", property="og:image")
        image_url = img_meta.get("content") if img_meta else None

        if name and price:
            return ProductData(
                name=name.strip(),
                price=price,
                currency=str(currency).strip() if currency else None,
                in_stock=True,
                url=url,
                image_url=image_url
            )
        return None
