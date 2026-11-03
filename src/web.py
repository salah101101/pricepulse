"""Web dashboard interface for PricePulse."""

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from src.extractors import fetch_page, get_extractor
from src.storage import PriceStorage

logger = logging.getLogger("pricepulse.web")

# Resolve template folder relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__, template_folder=str(PROJECT_ROOT / "templates"))


def get_combined_items() -> List[Dict[str, Any]]:
    from main import load_config
    config = load_config()
    storage = PriceStorage()
    products = config.get("products", [])
    default_threshold = config.get("default_discount_threshold", 10.0)

    items = []
    for p in products:
        url = p.get("url")
        threshold = p.get("discount_threshold", default_threshold)
        record = storage.get_item(url)

        if record:
            initial = Decimal(record.get("initial_price", "0"))
            last = Decimal(record.get("last_price", "0"))
            discount = Decimal("0")
            if initial > 0 and last < initial:
                discount = ((initial - last) / initial) * Decimal("100")

            items.append({
                "url": url,
                "name": record.get("name", url),
                "initial_price": f"{initial:.2f}",
                "last_price": f"{last:.2f}",
                "currency": record.get("currency", ""),
                "in_stock": record.get("in_stock", True),
                "threshold": threshold,
                "discount_percent": f"{discount:.1f}" if discount > 0 else None,
                "image_url": record.get("image_url")
            })
        else:
            items.append({
                "url": url,
                "name": url,
                "initial_price": "N/A",
                "last_price": "Pending",
                "currency": "",
                "in_stock": True,
                "threshold": threshold,
                "discount_percent": None,
                "image_url": None
            })

    return items


@app.route("/")
def index():
    from main import load_config
    config = load_config()
    items = get_combined_items()
    drops_count = sum(1 for i in items if i.get("discount_percent") is not None)

    return render_template(
        "dashboard.html",
        items=items,
        drops_count=drops_count,
        default_threshold=config.get("default_discount_threshold", 10.0)
    )


@app.route("/api/products", methods=["POST"])
def add_product_api():
    from main import add_product, fetch_page, get_extractor
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    threshold = data.get("threshold")

    if not url:
        return jsonify({"error": "Product URL is required"}), 400

    add_product(url, threshold)

    # Attempt immediate metadata fetch so the card renders with name/image right away
    try:
        html = fetch_page(url)
        if html:
            extractor = get_extractor(url)
            pdata = extractor.extract(html, url)
            if pdata:
                storage = PriceStorage()
                storage.record_price(pdata)
                record = storage.get_item(url)
                if record and pdata.image_url:
                    record["image_url"] = pdata.image_url
                    storage.save()
    except Exception as e:
        logger.warning("Could not pre-fetch item %s: %s", url, e)

    return jsonify({"success": True})


@app.route("/api/products/delete", methods=["POST"])
def delete_product_api():
    from main import load_config, save_config
    data = request.get_json() or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    config = load_config()
    products = config.get("products", [])
    config["products"] = [p for p in products if p.get("url") != url]
    save_config(config)

    return jsonify({"success": True})


@app.route("/api/check", methods=["POST"])
def run_check_api():
    from main import run_check
    try:
        run_check()
        return jsonify({"success": True})
    except Exception as e:
        logger.error("Price check cycle failed: %s", e)
        return jsonify({"error": str(e)}), 500


def start_dashboard(host: str = "127.0.0.1", port: int = 5000) -> None:
    print(f"\nPricePulse dashboard running at: http://{host}:{port}")
    print("Press Ctrl+C to stop the server.\n")
    app.run(host=host, port=port, debug=False)
