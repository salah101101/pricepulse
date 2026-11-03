"""Telegram notification dispatch."""

import logging
from decimal import Decimal
from typing import Optional
import requests

from src.extractors.base import ProductData

logger = logging.getLogger("pricepulse.notifier")


class TelegramNotifier:
    """Sends price alerts to a Telegram chat using standard Bot API."""

    def __init__(self, token: str, chat_id: str):
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        self.api_base = f"https://api.telegram.org/bot{self.token}"

    def send_price_drop_alert(
        self,
        product: ProductData,
        initial_price: Decimal,
        previous_price: Decimal,
        discount_percent: Decimal
    ) -> bool:
        """Send formatted alert for a detected price drop."""
        curr_str = f" {product.currency}" if product.currency else ""
        caption = (
            "PRICE DROP ALERT\n\n"
            f"Product: {product.name}\n"
            f"Current Price: {product.price:.2f}{curr_str}\n"
            f"Previous Price: {previous_price:.2f}{curr_str}\n"
            f"Initial Price: {initial_price:.2f}{curr_str}\n"
            f"Discount: {discount_percent:.1f}%\n\n"
            f"Link: {product.url}"
        )

        if product.image_url:
            success = self._send_photo(product.image_url, caption)
            if success:
                return True

        return self._send_message(caption)

    def send_stock_alert(self, product: ProductData) -> bool:
        """Send formatted alert when an out-of-stock item returns to stock."""
        curr_str = f" {product.currency}" if product.currency else ""
        caption = (
            "ITEM BACK IN STOCK\n\n"
            f"Product: {product.name}\n"
            f"Price: {product.price:.2f}{curr_str}\n\n"
            f"Link: {product.url}"
        )
        if product.image_url:
            success = self._send_photo(product.image_url, caption)
            if success:
                return True
        return self._send_message(caption)

    def _send_message(self, text: str) -> bool:
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                logger.info("Notification sent successfully.")
                return True
            logger.error("Telegram API error (%s): %s", res.status_code, res.text)
            return False
        except requests.RequestException as e:
            logger.error("Failed to connect to Telegram API: %s", e)
            return False

    def _send_photo(self, photo_url: str, caption: str) -> bool:
        url = f"{self.api_base}/sendPhoto"
        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.status_code == 200
        except requests.RequestException:
            return False
