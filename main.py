"""PricePulse - Lightweight, disciplined e-commerce price monitor."""

import argparse
import json
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from src.extractors import fetch_page, get_extractor
from src.notifier import TelegramNotifier
from src.storage import PriceStorage

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pricepulse")

CONFIG_PATH = Path("config.json")


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        default_config = {
            "default_discount_threshold": 10.0,
            "products": []
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        return default_config

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse config.json: %s", e)
        sys.exit(1)


def save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_notifier() -> TelegramNotifier:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. "
            "Alerts will be logged to console only. Set them in .env to enable Telegram."
        )
        return None

    return TelegramNotifier(token=token, chat_id=chat_id)


def run_check() -> None:
    config = load_config()
    products: List[Dict[str, Any]] = config.get("products", [])
    default_threshold = Decimal(str(config.get("default_discount_threshold", 10.0)))

    if not products:
        logger.info("No products configured. Use 'python main.py --add <url>' to add items.")
        return

    storage = PriceStorage()
    notifier = get_notifier()

    logger.info("Starting check for %d product(s)...", len(products))

    for item in products:
        url = item.get("url")
        if not url:
            continue

        item_threshold = Decimal(str(item.get("discount_threshold", default_threshold)))
        logger.info("Checking: %s", url)

        html = fetch_page(url)
        if not html:
            logger.warning("Skipping %s due to fetch failure.", url)
            continue

        extractor = get_extractor(url)
        product_data = extractor.extract(html, url)

        if not product_data:
            logger.warning("Could not extract price from %s.", url)
            continue

        is_new, prev_price, curr_price = storage.record_price(product_data)
        record = storage.get_item(url) or {}
        initial_price = Decimal(record.get("initial_price", str(curr_price)))

        curr_currency = product_data.currency or ""
        logger.info(
            "Product: '%s' | Current Price: %.2f %s",
            product_data.name,
            curr_price,
            curr_currency
        )

        if is_new:
            logger.info("Initialized baseline record for '%s'.", product_data.name)
            continue

        if prev_price is not None and curr_price < prev_price:
            # Calculate discount from initial baseline
            if initial_price > 0:
                discount = ((initial_price - curr_price) / initial_price) * Decimal("100")
            else:
                discount = Decimal("0")

            logger.info(
                "Price drop detected! Previous: %.2f, Current: %.2f (Discount: %.1f%%)",
                prev_price,
                curr_price,
                discount
            )

            if discount >= item_threshold:
                logger.info("Discount meets threshold (>= %.1f%%). Triggering notification.", item_threshold)
                if notifier:
                    notifier.send_price_drop_alert(
                        product=product_data,
                        initial_price=initial_price,
                        previous_price=prev_price,
                        discount_percent=discount
                    )
            else:
                logger.info("Discount (%.1f%%) is below configured threshold (%.1f%%).", discount, item_threshold)


def add_product(url: str, threshold: float = None) -> None:
    config = load_config()
    existing_urls = {p.get("url") for p in config.get("products", [])}

    if url in existing_urls:
        logger.info("Product URL already exists in config.")
        return

    entry = {"url": url}
    if threshold is not None:
        entry["discount_threshold"] = threshold

    config.setdefault("products", []).append(entry)
    save_config(config)
    logger.info("Successfully added product: %s", url)


def list_products() -> None:
    config = load_config()
    storage = PriceStorage()
    products = config.get("products", [])

    if not products:
        print("No products currently tracked.")
        return

    print("\nCurrently Tracked Products:")
    print("-" * 70)
    for idx, item in enumerate(products, 1):
        url = item.get("url")
        threshold = item.get("discount_threshold", config.get("default_discount_threshold", 10.0))
        record = storage.get_item(url)

        if record:
            name = record.get("name", "Unknown")
            last_price = record.get("last_price", "N/A")
            currency = record.get("currency", "")
            last_checked = record.get("last_checked", "Never")
            print(f"{idx}. {name}")
            print(f"   URL: {url}")
            print(f"   Last Price: {last_price} {currency} | Threshold: -{threshold}%")
            print(f"   Last Checked: {last_checked}\n")
        else:
            print(f"{idx}. (Pending First Check)")
            print(f"   URL: {url}")
            print(f"   Threshold: -{threshold}%\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="PricePulse - Daily e-commerce price drop tracker")
    parser.add_argument("--add", help="Add a product URL to the tracking list")
    parser.add_argument("--threshold", type=float, help="Discount percentage threshold for this product (e.g. 15.0)")
    parser.add_argument("--list", action="store_true", help="List all tracked products and their latest status")
    parser.add_argument("--check", action="store_true", help="Run a manual price check cycle immediately")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test notification to verify Telegram setup")
    parser.add_argument("--dashboard", action="store_true", help="Launch interactive web dashboard")
    parser.add_argument("--port", type=int, default=5000, help="Port for the web dashboard (default: 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for the web dashboard (default: 127.0.0.1)")

    args = parser.parse_args()

    if args.dashboard:
        from src.web import start_dashboard
        start_dashboard(host=args.host, port=args.port)
    elif args.add:
        add_product(args.add, args.threshold)
    elif args.list:
        list_products()
    elif args.test_telegram:
        notifier = get_notifier()
        if not notifier:
            print("Telegram credentials are not configured in .env.")
            sys.exit(1)
        ok = notifier._send_message("PricePulse test notification: connection verified successfully.")
        if ok:
            print("Test notification sent successfully.")
        else:
            print("Failed to send test notification. Check your token and chat ID.")
    else:
        # Default action: run check
        run_check()


if __name__ == "__main__":
    main()
