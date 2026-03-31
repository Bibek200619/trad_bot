# Binance Futures Testnet Trading Bot

Small Python CLI application for placing `MARKET` and `LIMIT` orders on Binance Futures Testnet (`USDⓈ-M`) with input validation, structured logging, and reusable API/client separation.

## Features

- Places `BUY` and `SELL` orders against `https://testnet.binancefuture.com`
- Supports `MARKET` and `LIMIT` order types
- Includes a lightweight Flask UI for manual order entry
- Validates symbols, quantity, price, and minimum notional against live `exchangeInfo`
- Logs API requests, responses, and failures to JSON log files
- Keeps the Binance client, validation, and CLI logic separate

## Project Structure

```text
trading_bot/
  bot/
    __init__.py
    client.py
    exceptions.py
    logging_config.py
    models.py
    orders.py
    response_utils.py
    runtime.py
    validators.py
  cli.py
  main.py
  web_ui.py
  README.md
  requirements.txt
  logs/
  static/
  templates/
```

## Requirements

- Python 3.11+ (tested here with Python 3.13)
- Binance Futures Testnet API key and secret

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Create a `.env` file from the example and fill in your Binance Futures Testnet credentials:

```bash
cp .env.example .env
```

```dotenv
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

The CLI loads `.env` automatically. Explicit CLI flags still work and take precedence over `.env`.

## Usage

### MARKET order example

```bash
.venv/bin/python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --order-type MARKET \
  --quantity 0.002 \
  --log-file logs/market_order.log
```

### LIMIT order example

```bash
.venv/bin/python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --order-type LIMIT \
  --quantity 0.002 \
  --price 95000 \
  --time-in-force GTC \
  --log-file logs/limit_order.log
```

You can also run the same CLI through `.venv/bin/python main.py ...`.

### Web UI

```bash
.venv/bin/python web_ui.py
```

Then open `http://127.0.0.1:5000` in your browser.

## CLI Arguments

- `--symbol`: futures symbol such as `BTCUSDT`
- `--side`: `BUY` or `SELL`
- `--order-type`: `MARKET` or `LIMIT`
- `--quantity`: order quantity
- `--price`: required for `LIMIT`, rejected for `MARKET`
- `--time-in-force`: optional for `LIMIT`, defaults to `GTC`
- `--log-file`: optional path for a JSON log file
- `--base-url`: override base URL if needed, defaults to Binance Futures Testnet

## Output

The CLI prints:

- an order request summary
- order response details including `orderId`, `status`, `executedQty`, and `avgPrice` when available
- a final `success` or `failure` message
- the log file path for the run

Each log line is JSON and records request metadata, response metadata, and stack traces for failures.

The web UI shows:

- the same order fields in a browser form
- live market context for the selected symbol
- success or failure state after submission
- normalized request details, response details, and the generated log file path

## Assumptions

- Orders are submitted in one-way mode without explicit `positionSide`.
- `LIMIT` orders default to `GTC`.
- Credentials are supplied through `.env`, environment variables, or CLI flags.
- Validation uses Binance public metadata from `exchangeInfo` and live ticker price for MARKET notional checks.

## Troubleshooting

- `code=-2015` / HTTP `401` means Binance rejected the signed request because the API key, secret, IP allowlist, or futures permissions are not valid for the testnet account.
- The repository includes a `logs/` directory and the CLI supports explicit log file names so you can keep one MARKET log and one LIMIT log for submission.
