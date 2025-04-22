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

- Python 3.7+
- API access to Kalshi and Polymarket
  - Kalshi API credentials (email and password)
  - Polymarket API key

## Installation

1. Clone this repository
   ```
   git clone https://github.com/your-username/prediction-market-arbitrage.git
   cd prediction-market-arbitrage
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

## Configuration

Run the application for the first time to access the configuration interface:

```
python run_arbitrage_checker.py
```

You'll need to provide:
- Kalshi API credentials
- Polymarket API key
- Check interval (in seconds)

## Usage

After configuration, the application will:
1. Fetch market data from both platforms
2. Identify similar markets
3. Detect arbitrage opportunities
4. Display results in a table format
5. Automatically rerun at the configured interval

## Sample Output

```
5 Arbitrage opportunities found!

   Kalshi Market                 Kalshi Side  Kalshi Price  Polymarket Market               Polymarket Side  Polymarket Price  Total Cost  Profit Potential
0  Will Trump win in 2024?       yes         0.65          2024 Presidential Election       no              0.32              0.97        0.03
1  Will Democrats win Senate?    no          0.45          Senate Control After Midterms    yes             0.52              0.97        0.03
2  Will inflation exceed 3%?     yes         0.72          CPI Inflation Rate Q4 2024       no              0.25              0.97        0.03
3  Fed rate hike in September?   no          0.82          Fed Rate Decision September      yes             0.15              0.97        0.03
4  Bitcoin > $100k by EOY?       yes         0.38          Bitcoin Price December 31, 2024  no              0.59              0.97        0.03
```

## Structure

- `kalshi_client.py` - API client for Kalshi
- `polymarket_client.py` - API client for Polymarket
- `market_processor.py` - Normalizes market data
- `arbitrage_detector.py` - Identifies opportunities
- `main.py` - Main application logic
- `config_ui.py` - Configuration interface
- `run_arbitrage_checker.py` - Entry point script

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