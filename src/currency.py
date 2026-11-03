"""Currency parsing and numeric normalization utilities."""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "₽": "RUB",
    "₩": "KRW",
    "₺": "TRY",
    "R$": "BRL",
    "C$": "CAD",
    "A$": "AUD",
}

COMMON_CODES = {
    "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "INR", "SAR", "AED", "KWD",
    "QAR", "BHD", "OMR", "EGP", "CHF", "CNY", "SEK", "NZD", "SGD", "HKD",
    "NOK", "MXN", "BRL", "ZAR", "TRY"
}


def parse_price(raw_text: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse a raw price text into an exact Decimal amount and currency code.

    Handles mixed international formats such as $1,299.99, 1.299,00 EUR,
    and single separator formats. Returns (None, None) if parsing fails.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None, None

    text = raw_text.strip()
    if not text:
        return None, None

    detected_currency = None

    # Check for 3-letter currency codes
    for code in COMMON_CODES:
        pattern = r"\b" + code + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            detected_currency = code.upper()
            break

    # If no 3-letter code found, check common symbols
    if not detected_currency:
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in text:
                detected_currency = code
                break

    # Extract numeric substring (digits, dots, commas)
    match = re.search(r"[\d\s.,]+", text)
    if not match:
        return None, detected_currency

    numeric_str = match.group(0).strip().replace(" ", "")
    if not numeric_str:
        return None, detected_currency

    # Normalize decimal and thousand separators
    has_comma = "," in numeric_str
    has_dot = "." in numeric_str

    if has_comma and has_dot:
        last_comma = numeric_str.rfind(",")
        last_dot = numeric_str.rfind(".")
        if last_dot > last_comma:
            # Standard 1,234.56
            clean_str = numeric_str.replace(",", "")
        else:
            # European 1.234,56
            clean_str = numeric_str.replace(".", "").replace(",", ".")
    elif has_comma and not has_dot:
        parts = numeric_str.split(",")
        if len(parts[-1]) == 2:
            # Likely European decimal: 19,99
            clean_str = numeric_str.replace(",", ".")
        else:
            # Likely thousand separator: 1,000
            clean_str = numeric_str.replace(",", "")
    elif has_dot and not has_comma:
        parts = numeric_str.split(".")
        if len(parts) > 2:
            # Multiple dots e.g. 1.000.000
            clean_str = "".join(parts[:-1]) + "." + parts[-1]
        else:
            clean_str = numeric_str
    else:
        clean_str = numeric_str

    # Final cleanup: keep only digits and single decimal point
    clean_str = re.sub(r"[^\d.]", "", clean_str)
    if not clean_str or clean_str == ".":
        return None, detected_currency

    try:
        amount = Decimal(clean_str).quantize(Decimal("0.01"))
        return amount, detected_currency
    except InvalidOperation:
        return None, detected_currency
