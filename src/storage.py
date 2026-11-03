"""State storage and price history manager."""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.extractors.base import ProductData

logger = logging.getLogger("pricepulse.storage")


class PriceStorage:
    """Manages persistent price records in a local JSON database."""

    def __init__(self, db_path: str = "database.json"):
        self.db_path = Path(db_path)
        self.data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            return {}
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read database file %s: %s", self.db_path, e)
            return {}

    def save(self) -> None:
        """Atomically persist state data to disk."""
        tmp_path = self.db_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            tmp_path.replace(self.db_path)
        except OSError as e:
            logger.error("Failed to write database file %s: %s", self.db_path, e)
            if tmp_path.exists():
                tmp_path.unlink()

    def get_item(self, url: str) -> Optional[Dict[str, Any]]:
        return self.data.get(url)

    def record_price(self, product: ProductData) -> Tuple[bool, Optional[Decimal], Decimal]:
        """Record a newly fetched price.

        Returns:
            (is_initial_check, previous_price, current_price)
        """
        now = datetime.now(timezone.utc).isoformat()
        current_price = product.price
        url = product.url

        if url not in self.data:
            # First time this product is checked
            self.data[url] = {
                "name": product.name,
                "initial_price": str(current_price),
                "lowest_price": str(current_price),
                "last_price": str(current_price),
                "currency": product.currency,
                "in_stock": product.in_stock,
                "image_url": product.image_url,
                "first_seen": now,
                "last_checked": now,
                "history": [
                    {"timestamp": now, "price": str(current_price)}
                ],
            }
            self.save()
            return True, None, current_price

        record = self.data[url]
        previous_price = Decimal(record.get("last_price", str(current_price)))
        lowest_price = Decimal(record.get("lowest_price", str(current_price)))

        # Update record
        record["name"] = product.name
        record["last_price"] = str(current_price)
        record["currency"] = product.currency or record.get("currency")
        record["in_stock"] = product.in_stock
        if product.image_url:
            record["image_url"] = product.image_url
        record["last_checked"] = now

        if current_price < lowest_price:
            record["lowest_price"] = str(current_price)

        if current_price != previous_price:
            record.setdefault("history", []).append({
                "timestamp": now,
                "price": str(current_price)
            })

        self.save()
        return False, previous_price, current_price
