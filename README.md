# Prediction Market Arbitrage Checker

A tool for identifying arbitrage opportunities between Kalshi and Polymarket prediction markets.

## Overview

This application automatically checks for price discrepancies between similar markets on Kalshi and Polymarket platforms, identifying potential arbitrage opportunities where the combined cost of opposing positions is less than 1.0 (indicating a guaranteed profit).

## Features

- Connects to both Kalshi and Polymarket APIs
- Normalizes market data from different platforms
- Identifies similar markets across platforms
- Detects arbitrage opportunities with calculated profit potential
- Automatically refreshes data at configurable intervals
- Simple configuration interface for API keys and settings

## Prerequisites

- Python 3.9.10 or higher (required for py-clob-client)
- API access to:
  - Kalshi
    - API Key
    - RSA Private Key (in PEM format)
  - Polymarket
    - Private Key

## Installation


1. Clone this repository
   ```bash
   git clone https://github.com/your-username/arbbot.git
   cd arbbot
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   pip install py-clob-client
   ```

4. Set up environment variables in a `.env` file:
   ```
   KALSHI_API_KEY=your_api_key
   POLYMARKET_PRIVATE_KEY=your_private_key
   ```

5. Place your Kalshi RSA private key in `kalshi_private_key.pem` in the project root

## Configuration

Run the application:

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run the application
python -m arbbot.run_arbitrage_checker
```

The following configuration options are available in `.env`:

- `KALSHI_API_KEY`: Your Kalshi API key
- `KALSHI_PRIVATE_KEY`: Path to your Kalshi RSA private key (default: `kalshi_private_key.pem`)
- `POLYMARKET_PRIVATE_KEY`: Your Polymarket private key
- `CHECK_INTERVAL`: Time between market checks in seconds (default: 300)
- `SIMILARITY_THRESHOLD`: Threshold for market title similarity (default: 0.8)
- `MIN_PROFIT_THRESHOLD`: Minimum profit percentage to report (default: 0.01)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: arbitrage_bot.log)

## Testing

To run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests (logs enabled by default)
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_polymarket_connection.py

# Run with verbose output
python -m pytest tests/ -v
```

## Usage

After configuration, the application will:

1. Connect to both Kalshi and Polymarket APIs
2. Fetch active markets from both platforms
3. Identify similar markets using text similarity
4. Calculate potential arbitrage opportunities
5. Display results in a rich table format
6. Automatically rerun at the configured interval

## Sample Output

```
🔍 Scanning markets for arbitrage opportunities...

┌────────────────────────────┬────────────┬─────────────┬─────────────────────────┬────────────────┬─────────────────┬────────────┐
│ Kalshi Market              │ Side       │ Price       │ Polymarket Market      │ Side           │ Price          │ Profit     │
├────────────────────────────┼────────────┼─────────────┼─────────────────────────┼────────────────┼─────────────────┼────────────┤
│ Will Trump win in 2024?    │ Yes        │ $0.65      │ 2024 Election          │ No            │ $0.32         │ 3.0%      │
│ BTC > $100k by Dec 2024   │ No         │ $0.82      │ Bitcoin EOY 2024       │ Yes           │ $0.15         │ 3.0%      │
└────────────────────────────┴────────────┴─────────────┴─────────────────────────┴────────────────┴─────────────────┴────────────┘
```

## Project Structure

```
.
├── src/
│   └── arbbot/
│       ├── __init__.py
│       ├── kalshi_client.py   # Kalshi API client
│       ├── polymarket_client.py # Polymarket API client
│       ├── config.py          # Configuration and environment variables
│       ├── main.py           # Core application logic
│       └── run_arbitrage_checker.py # Entry point script
├── tests/
│   ├── __init__.py
│   ├── test_auth.py          # Authentication tests
│   ├── test_market_integration.py  # Market data tests
│   ├── test_polymarket_connection.py # Polymarket API tests
│   └── test_polymarket_get_markets.py # Market fetching tests
├── .env                      # Environment variables
├── kalshi_private_key.pem    # Kalshi RSA private key
├── requirements.txt          # Python dependencies
└── README.md                 
```
## Limitations

- Market matching is based on simple string matching and may miss some opportunities
- No automatic trading capabilities (manual execution required)
- Trading fees are not accounted for in profit calculations
- Limited error handling in the basic implementation

## Future Improvements

- Advanced market matching using NLP
- Automated trading execution
- Web interface for monitoring
- Email/SMS notifications for high-profit opportunities
- Historical data tracking
- Risk management features

## License

MIT License

## Disclaimer

This tool is provided for educational purposes only. Trading in prediction markets involves risk. Always verify opportunities manually before executing trades. The creators assume no responsibility for financial losses.