"""Unit tests for PricePulse core modules."""

import unittest
from decimal import Decimal
import tempfile
import os

from src.currency import parse_price
from src.extractors.base import ProductData
from src.extractors.metadata import MetadataExtractor
from src.storage import PriceStorage


class TestCurrencyParser(unittest.TestCase):
    def test_standard_us_price(self):
        amount, curr = parse_price("$19.99")
        self.assertEqual(amount, Decimal("19.99"))
        self.assertEqual(curr, "USD")

    def test_comma_thousand_separator(self):
        amount, curr = parse_price("$1,299.50")
        self.assertEqual(amount, Decimal("1299.50"))
        self.assertEqual(curr, "USD")

    def test_european_format(self):
        amount, curr = parse_price("1.499,00 €")
        self.assertEqual(amount, Decimal("1499.00"))
        self.assertEqual(curr, "EUR")

    def test_gbp_symbol(self):
        amount, curr = parse_price("£45.00")
        self.assertEqual(amount, Decimal("45.00"))
        self.assertEqual(curr, "GBP")

    def test_text_code(self):
        amount, curr = parse_price("SAR 250.75")
        self.assertEqual(amount, Decimal("250.75"))
        self.assertEqual(curr, "SAR")


class TestMetadataExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = MetadataExtractor()

    def test_json_ld_extraction(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org/",
                "@type": "Product",
                "name": "Wireless Noise Cancelling Headphones",
                "image": "https://example.com/headphones.jpg",
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "USD",
                    "price": "149.99",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        data = self.extractor.extract(html, "https://example.com/item")
        self.assertIsNotNone(data)
        self.assertEqual(data.name, "Wireless Noise Cancelling Headphones")
        self.assertEqual(data.price, Decimal("149.99"))
        self.assertEqual(data.currency, "USD")
        self.assertTrue(data.in_stock)
        self.assertEqual(data.image_url, "https://example.com/headphones.jpg")

    def test_opengraph_fallback(self):
        html = """
        <html>
        <head>
            <meta property="og:title" content="Mechanical Keyboard" />
            <meta property="product:price:amount" content="89.50" />
            <meta property="product:price:currency" content="USD" />
            <meta property="og:image" content="https://example.com/kb.jpg" />
        </head>
        <body></body>
        </html>
        """
        data = self.extractor.extract(html, "https://example.com/keyboard")
        self.assertIsNotNone(data)
        self.assertEqual(data.name, "Mechanical Keyboard")
        self.assertEqual(data.price, Decimal("89.50"))
        self.assertEqual(data.currency, "USD")


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.tmp_file.close()
        self.storage = PriceStorage(db_path=self.tmp_file.name)

    def tearDown(self):
        if os.path.exists(self.tmp_file.name):
            os.remove(self.tmp_file.name)

    def test_price_recording(self):
        product1 = ProductData(
            name="Test Shoe",
            price=Decimal("100.00"),
            currency="USD",
            in_stock=True,
            url="https://example.com/shoe"
        )
        is_new, prev, curr = self.storage.record_price(product1)
        self.assertTrue(is_new)
        self.assertIsNone(prev)
        self.assertEqual(curr, Decimal("100.00"))

        # Subsequent check with lower price
        product2 = ProductData(
            name="Test Shoe",
            price=Decimal("80.00"),
            currency="USD",
            in_stock=True,
            url="https://example.com/shoe"
        )
        is_new, prev, curr = self.storage.record_price(product2)
        self.assertFalse(is_new)
        self.assertEqual(prev, Decimal("100.00"))
        self.assertEqual(curr, Decimal("80.00"))


class TestWebEndpoints(unittest.TestCase):
    def setUp(self):
        from src.web import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_dashboard_get(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"PricePulse", res.data)

    def test_add_delete_api(self):
        res = self.client.post("/api/products", json={"url": "https://example.com/test-prod", "threshold": 12.0})
        self.assertEqual(res.status_code, 200)

        del_res = self.client.post("/api/products/delete", json={"url": "https://example.com/test-prod"})
        self.assertEqual(del_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
