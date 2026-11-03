# PricePulse

A lightweight, automated e-commerce price monitor and drop alert system built in Python.

PricePulse runs periodically (e.g. once a day), inspects product URLs across thousands of online stores, detects price drops using structured web metadata (JSON-LD / Schema.org), and sends instant notifications to your Telegram account when a discount threshold is met.

## Features

- Universal Store Coverage: Uses semantic metadata standards (Schema.org JSON-LD, Microdata, OpenGraph) to support Shopify, WooCommerce, Magento, and independent e-commerce stores out of the box without store-specific code.
- Dedicated Platform Adapters: Specialized parsers for complex stores (such as Amazon) to handle custom DOM structures.
- Financial Precision: Built with Python's `Decimal` module to prevent IEEE 754 floating-point rounding errors during percentage and price calculations.
- Anti-Bot Resilience: Employs TLS fingerprint impersonation and realistic browser headers via `curl_cffi` to avoid automated scrapers being blocked.
- Percentage-Based Alerts: Configure a minimum discount threshold (e.g. notify only if price drops by at least 15%) rather than manually guessing target prices.
- Low Resource Footprint: Designed to run as a single daily batch task and exit immediately. No heavy browser automation or background RAM consumption.
- Telegram Alerts: Delivers clean, formatted messages with product image, old price, new price, and discount percentage.

## Requirements

- Python 3.10+
- Telegram Bot Token & Chat ID (free to create via `@BotFather` and `@userinfobot`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pricepulse.git
cd pricepulse
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Open `.env` and fill in your Telegram credentials:
```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_CHAT_ID=987654321
```

## Usage

### 1. Test Telegram Connection
Verify your credentials before starting tracking:
```bash
python main.py --test-telegram
```

### 2. Add Products
Add items with an optional discount threshold (default is 10%):
```bash
python main.py --add "https://example.com/product/running-shoes" --threshold 15
```

You can also edit `config.json` directly:
```json
{
  "default_discount_threshold": 10.0,
  "products": [
    {
      "url": "https://example.com/product/item-1",
      "discount_threshold": 20.0
    },
    {
      "url": "https://www.amazon.com/dp/B08N5WRWNW",
      "discount_threshold": 10.0
    }
  ]
}
```

### 3. Web Dashboard (Interactive Management)
Launch the local dark-themed web dashboard to visually manage products and trigger checks:
```bash
python main.py --dashboard
```
Open your browser at `http://127.0.0.1:5000` to track items, view discount badges, see product images, and trigger checks with a single click.

### 4. View Monitored Items (CLI)
List all configured products and their latest recorded prices:
```bash
python main.py --list
```

### 5. Run Manual Check
Run a single check across all items:
```bash
python main.py --check
```

## Scheduling Daily Checks

Because PricePulse is designed for disciplined daily checks, you can schedule it using your operating system's native task runner.

### Windows (Task Scheduler)
Create a scheduled task via PowerShell to run daily at 9:00 AM:
```powershell
$Action = New-ScheduledTaskAction -Execute "C:\path\to\pricepulse\venv\Scripts\python.exe" -Argument "main.py" -WorkingDirectory "C:\path\to\pricepulse"
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
Register-ScheduledTask -TaskName "PricePulseDaily" -Action $Action -Trigger $Trigger
```

### Linux / macOS (Cron)
Add an entry to crontab (`crontab -e`) to execute every morning at 9:00 AM:
```cron
0 9 * * * cd /path/to/pricepulse && ./venv/bin/python main.py >> pricepulse.log 2>&1
```

## Project Structure

```text
pricepulse/
├── config.json         # User configuration and tracked URL list
├── database.json       # Local state persistence (ignored in git)
├── requirements.txt    # Project dependencies
├── .env.example        # Telegram configuration template
├── .gitignore          # Standard repository exclusions
├── main.py             # CLI entrypoint and orchestrator
└── src/
    ├── currency.py     # Numeric parsing and currency normalization
    ├── notifier.py     # Telegram alert dispatcher
    ├── storage.py      # JSON state management and history tracking
    └── extractors/     # Multi-layer product data extraction engine
        ├── base.py     # Base extractor interface and HTTP fetching
        ├── metadata.py # Universal Schema.org / JSON-LD / Microdata engine
        └── amazon.py   # Dedicated Amazon DOM adapter
```

## License

MIT License. See LICENSE for details.
